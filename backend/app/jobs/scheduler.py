"""APScheduler wiring for the fast in-process intervals from section 8.6.
cron-job.org covers the slower/cross-restart intervals (heartbeat daily,
sync-events every 5 min, sla hourly) via the `/jobs/*` endpoints; this
in-process scheduler only matters while the single Render instance is awake,
and uses much faster demo intervals when DEMO_MODE=true.
"""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = AsyncIOScheduler()

    heartbeat_secs = 30 if settings.DEMO_MODE else 24 * 3600
    sync_secs = 10 if settings.DEMO_MODE else 60
    tx_watch_secs = 15
    finalize_secs = 60 if settings.DEMO_MODE else 60

    async def _job_heartbeat():
        from app.jobs.heartbeat import run_heartbeat_batch

        try:
            await run_heartbeat_batch()
        except Exception:
            logger.exception("scheduled_heartbeat_failed")

    async def _job_sync_events():
        from app.services.chain.event_sync import sync_all

        try:
            sync_all()
        except Exception:
            logger.exception("scheduled_sync_events_failed")

    async def _job_tx_watcher():
        from app.jobs.tx_watcher import run_tx_watcher

        try:
            await run_tx_watcher()
        except Exception:
            logger.exception("scheduled_tx_watcher_failed")

    async def _job_auto_finalize():
        from app.jobs.auto_finalize import run_auto_finalize

        try:
            await run_auto_finalize()
        except Exception:
            logger.exception("scheduled_auto_finalize_failed")

    scheduler.add_job(_job_heartbeat, "interval", seconds=heartbeat_secs, id="heartbeat_batch", max_instances=1)
    scheduler.add_job(_job_sync_events, "interval", seconds=sync_secs, id="event_sync", max_instances=1)
    scheduler.add_job(_job_tx_watcher, "interval", seconds=tx_watch_secs, id="tx_watcher", max_instances=1)
    scheduler.add_job(_job_auto_finalize, "interval", seconds=finalize_secs, id="auto_finalize", max_instances=1)

    scheduler.start()
    logger.info(
        "scheduler_started",
        demo_mode=settings.DEMO_MODE,
        heartbeat_secs=heartbeat_secs,
        sync_secs=sync_secs,
        tx_watch_secs=tx_watch_secs,
        finalize_secs=finalize_secs,
    )
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
