import logging
import time
from typing import Any, Generator

import httpx

from src.config import GITHUB_TOKEN

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"
PER_PAGE = 100
RATE_LIMIT_BUFFER = 100  # sleep when fewer than this many requests remain


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token or GITHUB_TOKEN
        if not self.token:
            raise ValueError("GITHUB_TOKEN is required. Set it in .env")
        self._client = httpx.Client(
            base_url=API_BASE,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        self._rate_remaining = 5000
        self._rate_reset = 0

    def _check_rate_limit(self, response: httpx.Response):
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        if remaining is not None:
            self._rate_remaining = int(remaining)
        if reset is not None:
            self._rate_reset = int(reset)

        if self._rate_remaining < RATE_LIMIT_BUFFER:
            wait_seconds = max(self._rate_reset - int(time.time()), 1) + 5
            logger.warning(
                "Rate limit low (%d remaining). Sleeping %d seconds.",
                self._rate_remaining, wait_seconds,
            )
            time.sleep(wait_seconds)

    def _get(self, url: str, params: dict | None = None, etag: str | None = None) -> httpx.Response:
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        response = self._client.get(url, params=params, headers=headers)
        self._check_rate_limit(response)
        return response

    def _paginate(
        self, url: str, params: dict | None = None, etag: str | None = None
    ) -> Generator[tuple[list[dict], str | None], None, None]:
        """Yield (items, etag) per page. Stops on 304 or last page."""
        params = dict(params or {})
        params.setdefault("per_page", PER_PAGE)
        page = 1

        while True:
            params["page"] = page
            resp = self._get(url, params=params, etag=etag if page == 1 else None)

            if resp.status_code == 304:
                logger.debug("304 Not Modified for %s", url)
                return

            if resp.status_code == 409:
                # Empty repository
                logger.debug("409 Conflict (empty repo) for %s", url)
                return

            resp.raise_for_status()
            data = resp.json()
            if not data:
                return

            new_etag = resp.headers.get("ETag")
            yield data, new_etag

            # Check for next page via Link header
            link = resp.headers.get("Link", "")
            if 'rel="next"' not in link:
                return
            page += 1

    def list_org_repos(self, org: str) -> list[dict[str, Any]]:
        """Fetch all repositories for the organization."""
        repos = []
        for page_data, _ in self._paginate(f"/orgs/{org}/repos", params={"type": "all", "sort": "pushed"}):
            repos.extend(page_data)
        logger.info("Fetched %d repos for org %s", len(repos), org)
        return repos

    def list_commits(
        self, owner: str, repo: str, since: str | None = None, etag: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch commits for a repo. Returns (commits, new_etag)."""
        params: dict[str, Any] = {}
        if since:
            params["since"] = since

        all_commits: list[dict] = []
        latest_etag: str | None = None

        for page_data, new_etag in self._paginate(
            f"/repos/{owner}/{repo}/commits", params=params, etag=etag
        ):
            all_commits.extend(page_data)
            if new_etag:
                latest_etag = new_etag

        return all_commits, latest_etag

    def get_commit_detail(self, owner: str, repo: str, sha: str) -> dict[str, Any]:
        """Fetch full commit details including stats and files."""
        resp = self._get(f"/repos/{owner}/{repo}/commits/{sha}")
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._client.close()
