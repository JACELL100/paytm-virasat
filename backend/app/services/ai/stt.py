"""Speech-to-text via Groq Whisper (section 12.4)."""
from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.groq_client import GroqNotConfigured, _get_client

logger = get_logger(__name__)


async def transcribe(audio_bytes: bytes, filename: str = "audio.webm", language_hint: Optional[str] = None) -> dict:
    """Returns {"text": str, "language": str}. Raises GroqNotConfigured if no
    GROQ_API_KEY -- callers (copilot voice endpoint) should return a 501/clear
    error until it's configured."""
    client = _get_client()  # raises GroqNotConfigured if unset
    kwargs = {
        "file": (filename, audio_bytes),
        "model": settings.GROQ_MODEL_STT,
        "response_format": "verbose_json",
    }
    if language_hint:
        kwargs["language"] = language_hint
    try:
        resp = await client.audio.transcriptions.create(**kwargs)
        return {"text": resp.text, "language": getattr(resp, "language", language_hint or "en")}
    except Exception:
        logger.warning("whisper_primary_model_failed_trying_fallback")
        kwargs["model"] = settings.GROQ_MODEL_STT_FALLBACK
        resp = await client.audio.transcriptions.create(**kwargs)
        return {"text": resp.text, "language": getattr(resp, "language", language_hint or "en")}
