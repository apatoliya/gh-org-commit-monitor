import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import POLL_INTERVAL_MINUTES
from src.collector.commit_fetcher import run_full_sync

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_full_sync,
        "interval",
        minutes=POLL_INTERVAL_MINUTES,
        id="commit_sync",
        name="GitHub Commit Sync",
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Scheduler started. Polling every %d minutes.", POLL_INTERVAL_MINUTES)

    # Run initial sync immediately
    logger.info("Running initial sync...")
    run_full_sync()


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped.")
