
import json
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.requests import Request

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.core.ratelimit import AI_RATE_LIMIT, limiter
from app.core.security import CurrentUser, get_current_user
from app.db.repos import copilot as copilot_repo
from app.db.repos import nominees as nominees_repo
from app.schemas.copilot import MessageIn, SessionCreateIn, SessionOut

logger = get_logger(__name__)
router = APIRouter(tags=["copilot"])

# Single-worker in-process cache: session_id -> decrypted manifest dict.
# The manifest is only ever decrypted through the Legacy Key unlock flow
# (see nominees.py); we cache it here for this session's lifetime so the
# co-pilot's tools don't need to re-prompt for the key on every turn. It is
# lost on process restart, matching section 4's "single Uvicorn worker" and
# section 11's "zero the DEK in memory" spirit (nothing persisted to disk).
_session_manifest_cache: dict[str, dict] = {}


class SessionCreateWithKeyIn(SessionCreateIn):
    legacy_key_share: Optional[str] = None


def _nominee_for_vault(user_id: str, vault_id: str) -> Optional[dict]:
    for r in nominees_repo.list_vaults_for_nominee_user(user_id):
        if r["vault_id"] == vault_id:
            return r
    return None


@router.post("/copilot/{vault_id}/sessions", response_model=SessionOut, status_code=201)
async def create_session(vault_id: str, body: SessionCreateWithKeyIn, user: CurrentUser = Depends(get_current_user)) -> SessionOut:
    nominee = _nominee_for_vault(user.id, vault_id)
    if not nominee:
        raise ApiError("not_a_nominee", "Forbidden", "You are not a nominee of this vault.", 403)

    session = copilot_repo.create_session(vault_id, user.id, body.language)

    if body.legacy_key_share:
        try:
            from app.api.v1.nominees import UnlockIn, unlock_vault

            unlocked = await unlock_vault(vault_id, UnlockIn(legacy_key_share=body.legacy_key_share), user)
            _session_manifest_cache[session["id"]] = unlocked.manifest
        except ApiError:
            raise
        except Exception:
            logger.exception("copilot_session_unlock_failed", vault_id=vault_id)

    return SessionOut.model_validate(session)


@router.post("/copilot/sessions/{session_id}/messages")
@limiter.limit(AI_RATE_LIMIT)
async def post_message(request: Request, session_id: str, body: MessageIn, user: CurrentUser = Depends(get_current_user)) -> StreamingResponse:
    session = copilot_repo.get_session(session_id)
    if not session or session.get("user_id") != user.id:
        raise ApiError("session_not_found", "Not found", "Copilot session not found.", 404)

    manifest = _session_manifest_cache.get(session_id, {})
    if not manifest:
        raise ApiError(
            "manifest_not_unlocked",
            "Conflict",
            "This session's vault hasn't been unlocked with a Legacy Key yet. Create a session with legacy_key_share, or call /nominee/vaults/{id}/unlock first.",
            409,
        )

    copilot_repo.add_message(session_id, "user", body.content)
    history = [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
        for m in copilot_repo.list_messages(session_id)[-10:]
        if m["role"] in ("user", "assistant")
    ][:-1]  # exclude the message we just added; it's passed separately

    from app.services.ai.copilot.agent import run_agent_turn

    async def event_stream():
        final_answer = ""
        tool_cards = []
        async for event in run_agent_turn(
            vault_id=session["vault_id"], nominee_id=user.id, manifest=manifest, language=session.get("language", "en"), history=history, user_message=body.content
        ):
            if event["type"] == "tool_card":
                tool_cards.append(event)
            if event["type"] == "answer":
                final_answer = event["text"]
            yield f"data: {json.dumps(event, default=str)}\n\n"

        copilot_repo.add_message(session_id, "assistant", final_answer, tool_calls=tool_cards)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/copilot/sessions/{session_id}/voice")
@limiter.limit(AI_RATE_LIMIT)
async def post_voice(request: Request, session_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    from fastapi import UploadFile

    form = await request.form()
    file: UploadFile = form.get("file")  # type: ignore[assignment]
    if file is None:
        raise ApiError("file_required", "Bad request", "Multipart field 'file' (audio) is required.", 400)

    session = copilot_repo.get_session(session_id)
    if not session or session.get("user_id") != user.id:
        raise ApiError("session_not_found", "Not found", "Copilot session not found.", 404)

    audio_bytes = await file.read()

    from app.services.ai.stt import transcribe

    try:
        result = await transcribe(audio_bytes, filename=file.filename or "audio.webm", language_hint=session.get("language"))
    except Exception as exc:
        raise ApiError("stt_failed", "Service unavailable", f"Speech-to-text failed or is not configured: {exc}", 503) from exc

    manifest = _session_manifest_cache.get(session_id, {})
    from app.services.ai.copilot.agent import run_agent_turn

    events = []
    final_answer = ""
    async for event in run_agent_turn(
        vault_id=session["vault_id"], nominee_id=user.id, manifest=manifest, language=result.get("language", session.get("language", "en")), history=[], user_message=result["text"]
    ):
        events.append(event)
        if event["type"] == "answer":
            final_answer = event["text"]

    audio_reply = None
    try:
        from app.services.ai.tts import synthesize

        audio_bytes_reply = await synthesize(final_answer, language=session.get("language", "en"))
        audio_reply = "generated" if audio_bytes_reply else None
    except Exception:
        audio_reply = None

    return {"transcript": result["text"], "language": result.get("language"), "events": events, "answer": final_answer, "tts": audio_reply or "browser_fallback"}
