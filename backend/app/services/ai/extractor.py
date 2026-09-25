"""Structured extraction from policy documents / death certificates, per
Implementation_Plan.md section 8.4 and section 12.2.

Pipeline: pdfplumber (text PDFs) -> vision model (scanned/image, via
`app.services.ai.vision`) -> Tesseract OCR fallback -> text LLM extraction.
Output is validated against `PolicyExtraction` / `DeathCertificateExtraction`
(app/schemas/documents.py). On validation failure, one repair call is made
(handled inside `chat_complete_json`), then the document is marked
`needs_review`.
"""
from __future__ import annotations

from typing import Optional

from app.core.logging import get_logger
from app.schemas.documents import DeathCertificateExtraction, PolicyExtraction
from app.services.ai.groq_client import GroqNotConfigured, chat_complete_json

logger = get_logger(__name__)

EXTRACT_POLICY_SYSTEM = (
    "Extract structured fields from the <document> policy text. Only use facts present "
    "in the text; use null for anything not stated. Return JSON matching the schema exactly."
)

EXTRACT_DEATH_CERT_SYSTEM = (
    "Extract structured fields from the <document> death certificate text. Only use facts "
    "present in the text; use null for anything not stated. Return JSON matching the schema exactly."
)


def extract_text_pdf(file_bytes: bytes) -> tuple[str, list[dict]]:
    """Returns (full_text, page_refs=[{page, text}]) using pdfplumber."""
    try:
        import io

        import pdfplumber

        pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append({"page": i + 1, "text": text})
        full_text = "\n\n".join(p["text"] for p in pages)
        return full_text, pages
    except Exception:
        logger.warning("pdfplumber_extract_failed")
        return "", []


async def extract_policy(document_text: str) -> PolicyExtraction:
    messages = [
        {"role": "system", "content": EXTRACT_POLICY_SYSTEM + "\n\nSchema: " + PolicyExtraction.model_json_schema().__str__()},
        {"role": "user", "content": f"<document>\n{document_text[:12000]}\n</document>"},
    ]
    try:
        return await chat_complete_json("extract", messages, PolicyExtraction)
    except GroqNotConfigured:
        logger.warning("extract_policy_ai_not_configured")
        return PolicyExtraction()
    except Exception:
        logger.exception("extract_policy_failed")
        return PolicyExtraction()


async def extract_death_certificate(document_text: str) -> DeathCertificateExtraction:
    messages = [
        {"role": "system", "content": EXTRACT_DEATH_CERT_SYSTEM + "\n\nSchema: " + DeathCertificateExtraction.model_json_schema().__str__()},
        {"role": "user", "content": f"<document>\n{document_text[:8000]}\n</document>"},
    ]
    try:
        return await chat_complete_json("extract", messages, DeathCertificateExtraction)
    except GroqNotConfigured:
        logger.warning("extract_death_cert_ai_not_configured")
        return DeathCertificateExtraction()
    except Exception:
        logger.exception("extract_death_cert_failed")
        return DeathCertificateExtraction()
