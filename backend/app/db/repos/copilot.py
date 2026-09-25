from __future__ import annotations

from typing import Any, Optional

from app.db.repos.base import require_client

SESSIONS_TABLE = "copilot_sessions"
MESSAGES_TABLE = "copilot_messages"


def create_session(vault_id: str, user_id: str, language: str) -> dict:
    client = require_client()
    res = client.table(SESSIONS_TABLE).insert(
        {"vault_id": vault_id, "user_id": user_id, "language": language}
    ).execute()
    return (res.data or [{}])[0]


def get_session(session_id: str) -> Optional[dict]:
    client = require_client()
    res = client.table(SESSIONS_TABLE).select("*").eq("id", session_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def add_message(session_id: str, role: str, content: str, tool_calls: Optional[list] = None, audio_path: Optional[str] = None) -> dict:
    client = require_client()
    res = client.table(MESSAGES_TABLE).insert(
        {
            "session_id": session_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls or [],
            "audio_path": audio_path,
        }
    ).execute()
    return (res.data or [{}])[0]


def list_messages(session_id: str) -> list[dict]:
    client = require_client()
    res = client.table(MESSAGES_TABLE).select("*").eq("session_id", session_id).order("created_at").execute()
    return res.data or []
