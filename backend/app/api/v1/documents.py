
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, Request, UploadFile

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.core.ratelimit import UPLOAD_RATE_LIMIT, limiter
from app.core.security import CurrentUser, get_current_user
from app.db.repos import documents as documents_repo
from app.schemas.documents import DocumentOut
from app.services.ai.extractor import extract_policy, extract_text_pdf
from app.services.ai.vision import pdf_to_images, vision_extract_text

logger = get_logger(__name__)
router = APIRouter(tags=["documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_KINDS = {"policy", "statement", "death_certificate", "id_proof", "other"}


def _sniff_type(content: bytes) -> Optional[str]:
    try:
        import filetype

        kind = filetype.guess(content)
        return kind.mime if kind else None
    except Exception:
        return None


def _upload_to_storage(bucket: str, path: str, content: bytes, content_type: str) -> Optional[str]:
    from app.db.client import get_supabase

    client = get_supabase()
    if client is None:
        logger.warning("document_storage_upload_skipped_no_db")
        return None
    try:
        client.storage.from_(bucket).upload(path, content, {"content-type": content_type, "upsert": "true"})
        return path
    except Exception:
        logger.warning("document_storage_upload_failed", bucket=bucket, path=path)
        return None


@router.post("/documents", response_model=DocumentOut, status_code=201)
@limiter.limit(UPLOAD_RATE_LIMIT)
async def upload_document(
    request: Request,
    file: UploadFile,
    kind: str = "policy",
    asset_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
) -> DocumentOut:
    if kind not in ALLOWED_KINDS:
        raise ApiError("invalid_kind", "Bad request", f"kind must be one of {sorted(ALLOWED_KINDS)}", 400)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ApiError("file_too_large", "Bad request", "File exceeds 10 MB limit.", 400)

    mime = _sniff_type(content)
    sha256 = hashlib.sha256(content).hexdigest()
    bucket = "death-certificates" if kind == "death_certificate" else "documents"
    storage_path = _upload_to_storage(bucket, f"{user.id}/{sha256}", content, mime or "application/octet-stream")

    doc = documents_repo.create_document(
        user.id,
        {
            "asset_id": asset_id,
            "kind": kind,
            "storage_path": storage_path or f"unstored/{sha256}",
            "sha256": sha256,
            "status": "processing",
        },
    )

    try:
        text, page_refs = extract_text_pdf(content) if (mime == "application/pdf" or (file.filename or "").lower().endswith(".pdf")) else ("", [])
        if not text.strip():
            images = pdf_to_images(content) if mime == "application/pdf" else [content]
            text = await vision_extract_text(images)

        if kind == "policy":
            extraction = await extract_policy(text)
            extracted = extraction.model_dump()
            status = "extracted" if extraction.insurer or extraction.policy_no else "needs_review"
        else:
            extracted = {"raw_text_preview": text[:2000]}
            status = "extracted" if text.strip() else "needs_review"

        chunks = [{"page": p.get("page"), "text": p.get("text", "")[:1200]} for p in page_refs] or (
            [{"page": 1, "text": text[:1200]}] if text else []
        )
        doc = documents_repo.update_document(doc["id"], {"extracted": extracted, "status": status, "chunks": chunks}) or doc
    except Exception:
        logger.exception("document_extraction_failed", document_id=doc["id"])
        doc = documents_repo.update_document(doc["id"], {"status": "needs_review"}) or doc

    return DocumentOut.model_validate(doc)


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, user: CurrentUser = Depends(get_current_user)) -> DocumentOut:
    doc = documents_repo.get_document(user.id, document_id)
    if not doc:
        raise ApiError("document_not_found", "Not found", "Document not found.", 404)
    return DocumentOut.model_validate(doc)
