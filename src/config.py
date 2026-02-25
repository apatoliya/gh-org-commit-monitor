import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_ORG = os.getenv("GITHUB_ORG", "")
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "30"))
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/commits.db")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8050"))
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
BACKFILL_DAYS = int(os.getenv("BACKFILL_DAYS", "90"))
