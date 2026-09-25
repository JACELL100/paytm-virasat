"""Parses bank statements (PDF via pdfplumber, CSV via pandas) into a list of
transaction rows: {date, narration, debit, credit}. Section 8.3 step 1."""
from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

DATE_PATTERNS = ["%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d/%m/%y", "%Y-%m-%d"]

ROW_REGEX = re.compile(
    r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(?P<narration>.+?)\s+"
    r"(?P<debit>[\d,]+\.\d{2})?\s*(?P<credit>[\d,]+\.\d{2})?\s*$"
)


def _parse_date(text: str) -> str | None:
    for fmt in DATE_PATTERNS:
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _clean_amount(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def parse_pdf_statement(file_bytes: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    for r in table:
                        parsed = _row_from_table_cells(r)
                        if parsed:
                            rows.append(parsed)
                if not tables:
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        m = ROW_REGEX.search(line)
                        if m:
                            d = _parse_date(m.group("date"))
                            if d:
                                rows.append(
                                    {
                                        "date": d,
                                        "narration": m.group("narration").strip(),
                                        "debit": _clean_amount(m.group("debit")),
                                        "credit": _clean_amount(m.group("credit")),
                                    }
                                )
    except Exception:
        logger.exception("parse_pdf_statement_failed")
    return rows


def _row_from_table_cells(cells: list[Any]) -> dict[str, Any] | None:
    cells = [c for c in cells if c is not None]
    if len(cells) < 3:
        return None
    date = _parse_date(str(cells[0]))
    if not date:
        return None
    narration = str(cells[1]) if len(cells) > 1 else ""
    debit = _clean_amount(str(cells[2])) if len(cells) > 2 else None
    credit = _clean_amount(str(cells[3])) if len(cells) > 3 else None
    return {"date": date, "narration": narration, "debit": debit, "credit": credit}


def parse_csv_statement(file_bytes: bytes) -> list[dict[str, Any]]:
    try:
        import pandas as pd

        df = pd.read_csv(io.BytesIO(file_bytes))
        df.columns = [c.strip().lower() for c in df.columns]
        date_col = next((c for c in df.columns if "date" in c), None)
        narr_col = next((c for c in df.columns if "narration" in c or "description" in c or "particulars" in c), None)
        debit_col = next((c for c in df.columns if "debit" in c or "withdrawal" in c), None)
        credit_col = next((c for c in df.columns if "credit" in c or "deposit" in c), None)

        rows = []
        for _, r in df.iterrows():
            date = _parse_date(str(r.get(date_col, ""))) if date_col else None
            if not date:
                continue
            rows.append(
                {
                    "date": date,
                    "narration": str(r.get(narr_col, "")) if narr_col else "",
                    "debit": _clean_amount(str(r.get(debit_col))) if debit_col and r.get(debit_col) else None,
                    "credit": _clean_amount(str(r.get(credit_col))) if credit_col and r.get(credit_col) else None,
                }
            )
        return rows
    except Exception:
        logger.exception("parse_csv_statement_failed")
        return []
