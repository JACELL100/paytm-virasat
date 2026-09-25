"""Wraps `groq.AsyncGroq` with the per-task model + fallback-chain config
from Implementation_Plan.md section 12.1.

Degrades gracefully: if GROQ_API_KEY isn't set, every call here raises
`GroqNotConfigured` (callers should catch this and fall back to a
deterministic/non-AI path, exactly like `insights.py` does for
`explain_gaps`).
"""
from __future__ import annotations

import json
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class GroqNotConfigured(Exception):
    pass


class GroqCallFailed(Exception):
    pass


_client = None


def _get_client():
    global _client
    if not settings.groq_configured:
        raise GroqNotConfigured("GROQ_API_KEY is not set.")
    if _client is None:
        from groq import AsyncGroq

        _client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _client


MODEL_CHAINS: dict[str, list[str]] = {
    "agent": [settings.GROQ_MODEL_AGENT, settings.GROQ_MODEL_AGENT_FALLBACK],
    "extract": [settings.GROQ_MODEL_EXTRACT, settings.GROQ_MODEL_EXTRACT_FALLBACK],
    "fast": [settings.GROQ_MODEL_FAST, settings.GROQ_MODEL_FAST_FALLBACK],
    "vision": [settings.GROQ_MODEL_VISION],
    "stt": [settings.GROQ_MODEL_STT, settings.GROQ_MODEL_STT_FALLBACK],
}


@retry(
    retry=retry_if_exception_type(GroqCallFailed),
    wait=wait_random_exponential(multiplier=1, max=8),
    stop=stop_after_attempt(2),
    reraise=True,
)
async def _call_one_model(model: str, messages: list[dict], *, json_mode: bool, temperature: float) -> str:
    client = _get_client()
    try:
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("groq_call_failed", model=model, error=str(exc))
        raise GroqCallFailed(str(exc)) from exc


async def chat_complete(task: str, messages: list[dict], *, json_mode: bool = False, temperature: float = 0.2) -> str:
    """Runs `messages` against the model chain for `task` ("agent" | "extract"
    | "fast" | "vision" | "stt"), falling back to the next model on failure."""
    chain = MODEL_CHAINS.get(task, MODEL_CHAINS["fast"])
    last_error: Optional[Exception] = None
    for model in chain:
        try:
            return await _call_one_model(model, messages, json_mode=json_mode, temperature=temperature)
        except GroqCallFailed as exc:
            last_error = exc
            continue
    raise GroqCallFailed(f"All models in chain {chain} failed for task {task!r}: {last_error}")


async def chat_complete_json(
    task: str, messages: list[dict], schema: Type[T], *, temperature: float = 0.1
) -> T:
    """JSON-mode call + Pydantic validation + one repair retry, per section 12.1."""
    raw = await chat_complete(task, messages, json_mode=True, temperature=temperature)
    try:
        return schema.model_validate_json(raw)
    except Exception as first_error:
        repair_messages = messages + [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": (
                    "That JSON did not match the required schema. Error: "
                    f"{first_error}\nReturn ONLY valid JSON matching the schema, nothing else."
                ),
            },
        ]
        raw2 = await chat_complete(task, repair_messages, json_mode=True, temperature=0.0)
        return schema.model_validate_json(raw2)


async def explain_gaps(*, score: int, gaps: list[dict], language: str = "en") -> str:
    """2-3 plain-language sentences explaining the Legacy Score & gaps, in the
    user's language (`explain_gaps.md`, task=fast). The score/gaps are always
    computed deterministically upstream -- this only explains them."""
    lang_name = {"en": "English", "hi": "Hindi", "mr": "Marathi"}.get(language, "English")
    gap_titles = "; ".join(g.get("title", "") for g in gaps[:3]) or "no major gaps"
    messages = [
        {
            "role": "system",
            "content": (
                "You are a calm, warm assistant explaining a family financial-protection score. "
                f"Reply in {lang_name}, 2-3 short plain sentences, no jargon, no alarm."
            ),
        },
        {
            "role": "user",
            "content": f"Legacy Score is {score} out of 100. Top gaps: {gap_titles}. Explain briefly and kindly.",
        },
    ]
    return await chat_complete("fast", messages, json_mode=False, temperature=0.4)
