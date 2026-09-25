"""Policy Q&A: BM25 retrieval over `documents.chunks` + an LLM answer with
page citations (`policy_qa.md`, section 8.2 `POST /assets/{id}/ask`,
section 12.2).
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.db.repos import documents as documents_repo
from app.services.ai.groq_client import GroqNotConfigured, chat_complete

logger = get_logger(__name__)


def _load_chunks(owner_id: str, asset_id: str) -> list[dict[str, Any]]:
    docs = documents_repo.list_documents(owner_id, asset_id=asset_id)
    chunks: list[dict[str, Any]] = []
    for d in docs:
        for c in d.get("chunks") or []:
            chunks.append({"text": c.get("text", ""), "page": c.get("page"), "document_id": d.get("id")})
    return chunks


def _bm25_top_k(question: str, chunks: list[dict[str, Any]], k: int = 5) -> list[dict[str, Any]]:
    if not chunks:
        return []
    try:
        from rank_bm25 import BM25Okapi

        tokenized = [c["text"].lower().split() for c in chunks]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(question.lower().split())
        ranked = sorted(zip(chunks, scores), key=lambda t: t[1], reverse=True)
        return [c for c, s in ranked[:k] if s > 0]
    except Exception:
        logger.warning("bm25_unavailable_falling_back_to_naive")
        return chunks[:k]


async def answer_policy_question(*, asset_id: str, question: str, owner_id: str) -> dict[str, Any]:
    chunks = _load_chunks(owner_id, asset_id)
    top = _bm25_top_k(question, chunks)

    if not top:
        return {
            "answer": "I don't have any extracted document text for this asset yet. Upload the policy document first.",
            "citations": [],
        }

    context = "\n\n".join(f"[p.{c.get('page', '?')}] {c['text']}" for c in top)
    citations = [f"p.{c.get('page', '?')}" for c in top]

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Answer the user's question about their policy using ONLY the provided "
                    "<document> excerpts. Cite the page like [p.X]. If unsure, say so plainly. "
                    "Never guarantee a payout amount -- say 'as per the policy document'."
                ),
            },
            {"role": "user", "content": f"<document>\n{context}\n</document>\n\nQuestion: {question}"},
        ]
        answer = await chat_complete("extract", messages, json_mode=False, temperature=0.1)
        return {"answer": answer, "citations": citations}
    except GroqNotConfigured:
        return {
            "answer": f"(AI not configured) Closest matching excerpt: {top[0]['text'][:400]}",
            "citations": citations,
        }
    except Exception:
        logger.exception("policy_qa_failed", asset_id=asset_id)
        return {"answer": "Sorry, I couldn't answer that right now. Please try again.", "citations": citations}
