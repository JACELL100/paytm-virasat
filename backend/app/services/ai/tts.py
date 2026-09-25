"""TTS via Sarvam Bulbul (optional, stretch item per section 2/12.4). If
SARVAM_API_KEY isn't set, callers should tell the frontend to use the
browser's SpeechSynthesis API instead (this returns None)."""
from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


async def synthesize(text: str, language: str = "hi") -> Optional[bytes]:
    """Returns raw audio bytes (WAV) from Sarvam Bulbul, or None if
    SARVAM_API_KEY isn't configured (frontend falls back to browser TTS)."""
    if not settings.SARVAM_API_KEY:
        logger.info("tts_sarvam_not_configured_frontend_should_fallback")
        return None
    try:
        import base64

        import httpx

        lang_code = {"hi": "hi-IN", "mr": "mr-IN", "en": "en-IN"}.get(language, "en-IN")
        payload = {"inputs": [text[:1500]], "target_language_code": lang_code, "speaker": "meera"}
        headers = {"API-Subscription-Key": settings.SARVAM_API_KEY, "content-type": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(SARVAM_TTS_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        audios = data.get("audios") or []
        if not audios:
            return None
        return base64.b64decode(audios[0])
    except Exception:
        logger.warning("sarvam_tts_failed")
        return None
