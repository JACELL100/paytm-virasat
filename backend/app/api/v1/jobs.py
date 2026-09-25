from __future__ import annotations

from fastapi import APIRouter, Header

from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.schemas.common import OkResponse

logger = get_logger(__name__)
router = APIRouter(tags=["jobs"])


def _check_cron_secret(x_cron_secret: str | None) -> None:
    if not settings.CRON_SECRET or x_cron_secret != settings.CRON_SECRET:
        raise ApiError("invalid_cron_secret", "Unauthorized", "Missing/invalid X-Cron-Secret header.", 401)


@router.post("/jobs/heartbeat", response_model=OkResponse)
async def job_heartbeat(x_cron_secret: str | None = Header(default=None)) -> OkResponse:
    _check_cron_secret(x_cron_secret)
    from app.jobs.heartbeat import run_heartbeat_batch

    result = await run_heartbeat_batch()
    return OkResponse(ok=True, detail=str(result))


@router.post("/jobs/sync-events", response_model=OkResponse)
async def job_sync_events(x_cron_secret: str | None = Header(default=None)) -> OkResponse:
    _check_cron_secret(x_cron_secret)
    from app.services.chain.event_sync import sync_all

    result = sync_all()
    return OkResponse(ok=True, detail=str(result))


@router.post("/jobs/sla", response_model=OkResponse)
async def job_sla(x_cron_secret: str | None = Header(default=None)) -> OkResponse:
    _check_cron_secret(x_cron_secret)
    from app.jobs.sla_watch import run_sla_watch

    result = await run_sla_watch()
    return OkResponse(ok=True, detail=str(result))
