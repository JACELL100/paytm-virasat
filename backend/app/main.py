from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import limiter

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", env=settings.ENV, demo_mode=settings.DEMO_MODE)

    if settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENV, traces_sample_rate=0.1)
            logger.info("sentry_initialized")
        except Exception:
            logger.exception("sentry_init_failed")

    if not settings.supabase_configured:
        logger.warning("startup_warning_supabase_not_configured")
    if not settings.groq_configured:
        logger.warning("startup_warning_groq_not_configured")
    if not settings.chain_configured:
        logger.warning("startup_warning_chain_not_configured")
    if not settings.wallet_enc_configured:
        logger.warning("startup_warning_wallet_enc_not_configured")

    scheduler = None
    try:
        from app.jobs.scheduler import start_scheduler

        scheduler = start_scheduler()
    except Exception:
        logger.exception("scheduler_start_failed")

    yield

    if scheduler is not None:
        try:
            from app.jobs.scheduler import stop_scheduler

            stop_scheduler()
        except Exception:
            logger.exception("scheduler_stop_failed")
    logger.info("shutdown")


app = FastAPI(
    title="Paytm Virasat API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={"type": "about:blank", "title": "Too many requests", "detail": str(exc.detail), "code": "rate_limited"},
    )


allowed_origins = list({settings.FRONTEND_ORIGIN, "http://localhost:3000"})
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["health"])
async def health() -> dict:
    from app.db.client import is_db_available
    from app.services.chain.web3_client import is_chain_available

    degraded = not (settings.supabase_configured and settings.groq_configured)
    return {
        "status": "degraded" if degraded else "ok",
        "env": settings.ENV,
        "demo_mode": settings.DEMO_MODE,
        "supabase_configured": settings.supabase_configured,
        "db_reachable": is_db_available(),
        "groq_configured": settings.groq_configured,
        "chain_configured": settings.chain_configured,
        "chain_reachable": is_chain_available(),
    }


def _include_routers() -> None:
    from app.api.v1 import (
        activity,
        assets,
        claims,
        copilot,
        demo,
        discovery,
        documents,
        guardians,
        insights,
        invites,
        jobs,
        me,
        nominees,
        vault,
        verify,
    )

    prefix = settings.API_V1_PREFIX
    app.include_router(me.router, prefix=prefix)
    app.include_router(activity.router, prefix=prefix)
    app.include_router(assets.router, prefix=prefix)
    app.include_router(insights.router, prefix=prefix)
    app.include_router(discovery.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(vault.router, prefix=prefix)
    app.include_router(invites.router, prefix=prefix)
    app.include_router(guardians.router, prefix=prefix)
    app.include_router(nominees.router, prefix=prefix)
    app.include_router(copilot.router, prefix=prefix)
    app.include_router(claims.router, prefix=prefix)
    app.include_router(verify.router, prefix=prefix)
    app.include_router(jobs.router, prefix=prefix)
    app.include_router(demo.router, prefix=prefix)


_include_routers()
