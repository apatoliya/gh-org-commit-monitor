#!/usr/bin/env python3
"""GitHub Organization Commit Monitor - CLI Entry Point.

Usage:
    python run.py collect              One-time sync of all repos
    python run.py dashboard            Start dashboard only
    python run.py serve                Run collector scheduler + dashboard
    python run.py backfill --since DATE  Historical backfill from DATE (YYYY-MM-DD)
"""

import argparse
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_collect(args):
    """Run a one-time sync."""
    from src.collector.commit_fetcher import run_full_sync
    total = run_full_sync()
    logger.info("Collection complete. %d new commits synced.", total)


def cmd_dashboard(args):
    """Start the dashboard server."""
    from src.dashboard.app import app
    from src.config import DASHBOARD_PORT, DASHBOARD_HOST
    logger.info("Starting dashboard at http://%s:%d", DASHBOARD_HOST, DASHBOARD_PORT)
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)


def cmd_serve(args):
    """Run both collector scheduler and dashboard."""
    from src.collector.scheduler import start_scheduler, stop_scheduler
    from src.dashboard.app import app
    from src.config import DASHBOARD_PORT, DASHBOARD_HOST

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        stop_scheduler()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    start_scheduler()
    logger.info("Starting dashboard at http://%s:%d", DASHBOARD_HOST, DASHBOARD_PORT)
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)


def cmd_backfill(args):
    """Run historical backfill from a specific date."""
    since = args.since + "T00:00:00Z"
    from src.collector.commit_fetcher import run_full_sync
    logger.info("Starting backfill from %s", args.since)
    total = run_full_sync(since=since)
    logger.info("Backfill complete. %d commits synced.", total)


def main():
    parser = argparse.ArgumentParser(description="GitHub Org Commit Monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("collect", help="Run one-time sync")
    subparsers.add_parser("dashboard", help="Start dashboard only")
    subparsers.add_parser("serve", help="Run collector + dashboard")

    backfill_parser = subparsers.add_parser("backfill", help="Historical backfill")
    backfill_parser.add_argument("--since", required=True, help="Start date (YYYY-MM-DD)")

    args = parser.parse_args()

    commands = {
        "collect": cmd_collect,
        "dashboard": cmd_dashboard,
        "serve": cmd_serve,
        "backfill": cmd_backfill,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
