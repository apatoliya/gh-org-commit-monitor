"""Seed the database with realistic sample data for screenshots."""

import random
import hashlib
from datetime import datetime, timedelta

import sys
sys.path.insert(0, ".")

from src.database import init_db, upsert_repo, upsert_commit

REPOS = [
    ("acme-org/api-gateway", "https://github.com/acme-org/api-gateway"),
    ("acme-org/web-dashboard", "https://github.com/acme-org/web-dashboard"),
    ("acme-org/auth-service", "https://github.com/acme-org/auth-service"),
    ("acme-org/data-pipeline", "https://github.com/acme-org/data-pipeline"),
    ("acme-org/mobile-app", "https://github.com/acme-org/mobile-app"),
    ("acme-org/infra-terraform", "https://github.com/acme-org/infra-terraform"),
    ("acme-org/ml-models", "https://github.com/acme-org/ml-models"),
    ("acme-org/docs-site", "https://github.com/acme-org/docs-site"),
    ("acme-org/cli-tool", "https://github.com/acme-org/cli-tool"),
    ("acme-org/shared-libs", "https://github.com/acme-org/shared-libs"),
    ("acme-org/event-bus", "https://github.com/acme-org/event-bus"),
    ("acme-org/notification-svc", "https://github.com/acme-org/notification-svc"),
]

AUTHORS = [
    ("Alice Chen", "alice@acme.dev", "alice-chen"),
    ("Bob Kumar", "bob@acme.dev", "bob-kumar"),
    ("Carol Zhang", "carol@acme.dev", "carol-zhang"),
    ("Dave Wilson", "dave@acme.dev", "dave-wilson"),
    ("Eve Martinez", "eve@acme.dev", "eve-martinez"),
    ("Frank Lee", "frank@acme.dev", "frank-lee"),
    ("Grace Park", "grace@acme.dev", "grace-park"),
    ("Hiro Tanaka", "hiro@acme.dev", "hiro-tanaka"),
    ("Ivy Scott", "ivy@acme.dev", "ivy-scott"),
    ("Jake Brown", "jake@acme.dev", "jake-brown"),
    ("Kara Singh", "kara@acme.dev", "kara-singh"),
    ("Leo Rivera", "leo@acme.dev", "leo-rivera"),
]

CLASSIFICATIONS = [
    ("human", 0.0, "none"),
    ("ai_claude", 1.0, "co_author_tag"),
    ("ai_copilot", 1.0, "co_author_tag"),
    ("ai_cursor", 0.85, "heuristic"),
    ("ai_cody", 0.9, "co_author_tag"),
    ("ai_aider", 0.8, "heuristic"),
    ("ai_gemini", 0.75, "heuristic"),
    ("ai_codex", 0.95, "co_author_tag"),
]

HUMAN_MESSAGES = [
    "fix: resolve null pointer in user login flow",
    "hotfix: patch XSS vulnerability in comment form",
    "fix: correct timezone offset in scheduling logic",
    "chore: bump dependencies to latest versions",
    "fix: handle edge case in payment retry logic",
    "style: align buttons in header nav",
    "fix: race condition in websocket reconnect",
    "docs: update API changelog for v2.4",
    "fix: memory leak in image processing worker",
    "perf: optimize database query for user search",
    "fix: broken redirect after OAuth callback",
    "chore: rotate API keys for staging environment",
    "fix: incorrect date parsing for ISO 8601 format",
    "refactor: simplify error handling middleware",
    "fix: prevent duplicate webhook deliveries",
]

AI_MESSAGES = [
    "feat: implement rate limiting middleware with sliding window algorithm",
    "feat: add comprehensive input validation for REST API endpoints",
    "refactor: restructure authentication module with strategy pattern",
    "feat: implement real-time notification system using WebSockets",
    "feat: add CSV export functionality with streaming for large datasets",
    "refactor: migrate database queries to use parameterized prepared statements",
    "feat: implement role-based access control with hierarchical permissions",
    "feat: add automated retry mechanism with exponential backoff",
    "test: add comprehensive unit tests for payment processing module",
    "feat: implement full-text search with relevance scoring",
    "refactor: convert callback-based code to async/await pattern",
    "feat: add GraphQL schema with resolver functions for user domain",
    "feat: implement audit logging system with structured event tracking",
    "feat: add health check endpoints with dependency status reporting",
    "docs: add comprehensive API documentation with usage examples",
]


def seed():
    init_db()

    repo_ids = {}
    for name, url in REPOS:
        repo_ids[name] = upsert_repo(name, url)

    random.seed(42)
    now = datetime.utcnow()

    # Generate ~800 commits over the last 90 days
    for i in range(800):
        days_ago = random.randint(0, 90)
        hours_ago = random.randint(0, 23)
        committed_at = now - timedelta(days=days_ago, hours=hours_ago)

        repo_name = random.choice(list(repo_ids.keys()))
        repo_id = repo_ids[repo_name]
        author = random.choice(AUTHORS)

        # ~30% AI-assisted, weighted by author
        author_idx = AUTHORS.index(author)
        ai_probability = 0.15 + (author_idx % 5) * 0.08  # 15-47% depending on author
        # Increase AI usage in recent weeks
        if days_ago < 30:
            ai_probability += 0.1

        if random.random() < ai_probability:
            cls, conf, method = random.choice(CLASSIFICATIONS[1:])  # skip human
            message = random.choice(AI_MESSAGES)
            # AI commits tend to have more additions
            additions = random.randint(50, 500)
            deletions = random.randint(10, 150)
            files_changed = random.randint(3, 20)
        else:
            cls, conf, method = CLASSIFICATIONS[0]
            message = random.choice(HUMAN_MESSAGES)
            additions = random.randint(5, 200)
            deletions = random.randint(2, 80)
            files_changed = random.randint(1, 10)

        sha = hashlib.sha256(f"{i}-{repo_name}-{committed_at}".encode()).hexdigest()[:40]

        upsert_commit(
            sha=sha,
            repo_id=repo_id,
            author_name=author[0],
            author_email=author[1],
            author_login=author[2],
            message=message,
            committed_at=committed_at,
            additions=additions,
            deletions=deletions,
            files_changed=files_changed,
            classification=cls,
            confidence=conf,
            detection_method=method,
        )

    print(f"Seeded {len(REPOS)} repos and 800 commits.")


if __name__ == "__main__":
    seed()
