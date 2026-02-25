import logging
from datetime import datetime, timedelta

from src.config import GITHUB_ORG, BACKFILL_DAYS
from src.database import (
    init_db, upsert_repo, upsert_commit, update_repo_fetched,
    get_sync_state, update_sync_state, get_repo_last_sha,
)
from src.collector.github_client import GitHubClient
from src.analyzer.tag_detector import detect_ai_tags
from src.analyzer.heuristic import classify_commit

logger = logging.getLogger(__name__)


def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def fetch_all_repos(client: GitHubClient, org: str | None = None) -> list[dict]:
    """Fetch all repos and upsert into database. Returns list of repo dicts."""
    org = org or GITHUB_ORG
    if not org:
        raise ValueError("GITHUB_ORG is required. Set it in .env")

    repos = client.list_org_repos(org)
    for repo in repos:
        upsert_repo(repo["full_name"], repo["html_url"])
    logger.info("Synced %d repos to database", len(repos))
    return repos


def fetch_repo_commits(client: GitHubClient, repo: dict, since: str | None = None):
    """Fetch new commits for a single repo and analyze them."""
    full_name = repo["full_name"]
    owner, repo_name = full_name.split("/", 1)

    # Get sync state for conditional requests
    sync = get_sync_state(full_name)
    etag = sync["etag"] if sync else None

    # Determine 'since' date
    if not since:
        if sync and sync.get("last_sync_at"):
            since = str(sync["last_sync_at"])
        else:
            since = (datetime.utcnow() - timedelta(days=BACKFILL_DAYS)).isoformat() + "Z"

    try:
        commits, new_etag = client.list_commits(owner, repo_name, since=since, etag=etag)
    except Exception as e:
        logger.error("Failed to fetch commits for %s: %s", full_name, e)
        return 0

    if not commits:
        update_sync_state(full_name, etag=new_etag or etag)
        return 0

    repo_id = upsert_repo(full_name, repo.get("html_url", ""))
    new_count = 0

    for commit_data in commits:
        sha = commit_data["sha"]
        commit_info = commit_data.get("commit", {})
        author = commit_info.get("author", {})
        gh_author = commit_data.get("author") or {}
        message = commit_info.get("message", "")

        # Run AI detection
        tag_result = detect_ai_tags(message)

        # Fetch diff for heuristic analysis only if no tag detected
        diff_text = None
        if not tag_result.detected:
            try:
                detail = client.get_commit_detail(owner, repo_name, sha)
                stats = detail.get("stats", {})
                files = detail.get("files", [])
                diff_text = "\n".join(f.get("patch", "") for f in files if f.get("patch"))
            except Exception:
                stats = {}
                files = []
        else:
            stats = commit_data.get("stats", {})
            files = commit_data.get("files", [])

        classification, confidence, detection_method = classify_commit(
            commit_message=message,
            diff_text=diff_text,
            tag_classification=tag_result.classification,
            tag_confidence=tag_result.confidence,
            tag_detected=tag_result.detected,
        )

        committed_at = _parse_datetime(author.get("date"))
        upsert_commit(
            sha=sha,
            repo_id=repo_id,
            author_name=author.get("name", ""),
            author_email=author.get("email", ""),
            author_login=gh_author.get("login", ""),
            message=message,
            committed_at=committed_at,
            additions=stats.get("additions", 0),
            deletions=stats.get("deletions", 0),
            files_changed=len(files) if isinstance(files, list) else 0,
            classification=classification,
            confidence=confidence,
            detection_method=detection_method,
        )
        new_count += 1

    # Update sync state
    latest_sha = commits[0]["sha"] if commits else None
    if latest_sha:
        update_repo_fetched(repo_id, latest_sha)
    update_sync_state(full_name, etag=new_etag or etag)

    logger.info("Processed %d new commits for %s", new_count, full_name)
    return new_count


def run_full_sync(org: str | None = None, since: str | None = None):
    """Run a full sync across all repos in the organization."""
    init_db()
    client = GitHubClient()

    try:
        repos = fetch_all_repos(client, org)
        total_new = 0

        for i, repo in enumerate(repos, 1):
            if repo.get("archived"):
                logger.debug("Skipping archived repo: %s", repo["full_name"])
                continue

            logger.info("[%d/%d] Processing %s", i, len(repos), repo["full_name"])
            new_count = fetch_repo_commits(client, repo, since=since)
            total_new += new_count

        logger.info("Sync complete. Total new commits: %d across %d repos", total_new, len(repos))
        return total_new
    finally:
        client.close()
