"""Scanned document / image handling: pypdfium2 (PDF->image) -> Groq vision
model -> Tesseract `eng+hin+mar` OCR fallback, per section 8.4 / 12.1.
"""
from __future__ import annotations

import base64
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.groq_client import GroqCallFailed, GroqNotConfigured, chat_complete

logger = get_logger(__name__)


def pdf_to_images(file_bytes: bytes, max_pages: int = 3) -> list[bytes]:
    try:
        import io

        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(file_bytes)
        images = []
        for i in range(min(len(pdf), max_pages)):
            page = pdf[i]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            images.append(buf.getvalue())
        return images
    except Exception:
        logger.warning("pdf_to_images_failed")
        return []


def tesseract_ocr(image_bytes: bytes) -> str:
    try:
        import io

        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img, lang="eng+hin+mar")
    except Exception:
        logger.warning("tesseract_ocr_unavailable_or_failed")
        return ""


async def vision_extract_text(images: list[bytes]) -> str:
    """Sends up to 3 images to the Groq vision model. Falls back to Tesseract
    OCR (then the text LLM downstream) on failure/429, per section 8.4."""
    if not images:
        return ""
    try:
        content = [{"type": "text", "text": "Transcribe all readable text from this document image, verbatim."}]
        for img in images[:3]:
            b64 = base64.b64encode(img).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
        messages = [{"role": "user", "content": content}]
        return await chat_complete("vision", messages, json_mode=False, temperature=0.0)
    except (GroqNotConfigured, GroqCallFailed):
        logger.warning("vision_extract_falling_back_to_ocr")
        return "\n".join(tesseract_ocr(img) for img in images)
    except Exception:
        logger.exception("vision_extract_unexpected_failure")
        return "\n".join(tesseract_ocr(img) for img in images)


def decode_qr(image_bytes: bytes) -> Optional[str]:
    """Decodes a QR code (Indian CRS death certificates usually carry a
    verification QR, section 12.5). Returns the decoded text/URL, or None if
    zxing-cpp isn't installed/no QR found -- callers should degrade to
    'QR decode unavailable' rather than fail the upload."""
    try:
        import io

        import zxingcpp
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        results = zxingcpp.read_barcodes(img)
        if results:
            return results[0].text
        return None
    except ImportError:
        logger.warning("zxing_cpp_not_installed")
        return None
    except Exception:
        logger.warning("qr_decode_failed")
        return None
