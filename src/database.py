import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    url TEXT,
    last_fetched_sha TEXT,
    last_fetched_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha TEXT UNIQUE NOT NULL,
    repo_id INTEGER NOT NULL REFERENCES repositories(id),
    author_name TEXT,
    author_email TEXT,
    author_login TEXT,
    message TEXT,
    committed_at TIMESTAMP,
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    classification TEXT DEFAULT 'human',
    confidence REAL DEFAULT 1.0,
    detection_method TEXT
);

CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_name TEXT UNIQUE NOT NULL,
    etag TEXT,
    last_page INTEGER DEFAULT 0,
    last_sync_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repo_id);
CREATE INDEX IF NOT EXISTS idx_commits_classification ON commits(classification);
CREATE INDEX IF NOT EXISTS idx_commits_committed_at ON commits(committed_at);
CREATE INDEX IF NOT EXISTS idx_commits_author_login ON commits(author_login);
"""


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with _get_conn() as conn:
        conn.executescript(_SCHEMA)


def upsert_repo(name: str, url: str) -> int:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO repositories (name, url) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET url=excluded.url",
            (name, url),
        )
        row = conn.execute(
            "SELECT id FROM repositories WHERE name = ?", (name,)
        ).fetchone()
        return row["id"]


def update_repo_fetched(repo_id: int, sha: str):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE repositories SET last_fetched_sha = ?, last_fetched_at = ? WHERE id = ?",
            (sha, datetime.utcnow(), repo_id),
        )


def get_repo_last_sha(repo_name: str) -> str | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT last_fetched_sha FROM repositories WHERE name = ?", (repo_name,)
        ).fetchone()
        return row["last_fetched_sha"] if row else None


def upsert_commit(
    sha: str,
    repo_id: int,
    author_name: str,
    author_email: str,
    author_login: str,
    message: str,
    committed_at: datetime,
    additions: int,
    deletions: int,
    files_changed: int,
    classification: str,
    confidence: float,
    detection_method: str,
):
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO commits
               (sha, repo_id, author_name, author_email, author_login,
                message, committed_at, additions, deletions, files_changed,
                classification, confidence, detection_method)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(sha) DO UPDATE SET
                 classification=excluded.classification,
                 confidence=excluded.confidence,
                 detection_method=excluded.detection_method""",
            (
                sha, repo_id, author_name, author_email, author_login,
                message, committed_at, additions, deletions, files_changed,
                classification, confidence, detection_method,
            ),
        )


def get_sync_state(repo_name: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT etag, last_page, last_sync_at FROM sync_state WHERE repo_name = ?",
            (repo_name,),
        ).fetchone()
        return dict(row) if row else None


def update_sync_state(repo_name: str, etag: str | None = None, last_page: int = 0):
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO sync_state (repo_name, etag, last_page, last_sync_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(repo_name) DO UPDATE SET
                 etag=excluded.etag, last_page=excluded.last_page,
                 last_sync_at=excluded.last_sync_at""",
            (repo_name, etag, last_page, datetime.utcnow()),
        )


def get_commits_df(
    start_date: str | None = None,
    end_date: str | None = None,
    repo_name: str | None = None,
    author_login: str | None = None,
) -> pd.DataFrame:
    query = """
        SELECT c.sha, r.name as repo_name, c.author_name, c.author_email,
               c.author_login, c.message, c.committed_at, c.additions,
               c.deletions, c.files_changed, c.classification, c.confidence,
               c.detection_method
        FROM commits c
        JOIN repositories r ON c.repo_id = r.id
        WHERE 1=1
    """
    params: list = []
    if start_date:
        query += " AND c.committed_at >= ?"
        params.append(start_date)
    if end_date:
        query += " AND c.committed_at <= ?"
        params.append(end_date)
    if repo_name:
        query += " AND r.name = ?"
        params.append(repo_name)
    if author_login:
        query += " AND c.author_login = ?"
        params.append(author_login)
    query += " ORDER BY c.committed_at DESC"

    with _get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params, parse_dates=["committed_at"])


def get_repo_names() -> list[str]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT name FROM repositories ORDER BY name").fetchall()
        return [r["name"] for r in rows]


def get_author_logins() -> list[str]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT author_login FROM commits WHERE author_login IS NOT NULL ORDER BY author_login"
        ).fetchall()
        return [r["author_login"] for r in rows]
