"""Sahayak's tools, per Implementation_Plan.md section 12.3.

Every function here is bound to a (vault_id, nominee_id) pair injected by the
router -- the model is never given a `vault_id` parameter to fill in, so it
can never address another vault (guardrail from section 12.3).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

from app.core.logging import get_logger
from app.db.repos import claims as claims_repo
from app.db.repos import institutions as institutions_repo

logger = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_claim_requirements_cache: Optional[dict[str, Any]] = None


def _load_claim_requirements() -> dict[str, Any]:
    global _claim_requirements_cache
    if _claim_requirements_cache is not None:
        return _claim_requirements_cache
    path = _DATA_DIR / "claim_requirements.json"
    if not path.exists():
        _claim_requirements_cache = {"generic_templates": {}, "escalation_contacts": {}}
    else:
        _claim_requirements_cache = json.loads(path.read_text(encoding="utf-8"))
    return _claim_requirements_cache


class CopilotTools:
    def __init__(self, *, vault_id: str, nominee_id: str, manifest: dict[str, Any]):
        self.vault_id = vault_id
        self.nominee_id = nominee_id
        self.manifest = manifest

    def get_asset_map(self) -> dict[str, Any]:
        return {"assets": self.manifest.get("assets", []), "owner": self.manifest.get("owner", {})}

    def get_claim_plan(self) -> dict[str, Any]:
        from app.services.scoring.claim_priority import rank_claims

        claims = []
        for a in self.manifest.get("assets", []):
            claims.append(
                {
                    "asset_id": a.get("id"),
                    "label": a.get("label"),
                    "asset_type": a.get("type", "other"),
                    "value_estimate": a.get("value_estimate"),
                    "required_docs": self.get_claim_requirements(a.get("id")).get("required_docs", []),
                    "available_docs": [],
                    "has_active_loan_protection": a.get("meta", {}).get("has_active_loan_protection", False),
                }
            )
        ranked = rank_claims(claims)
        return {"claims": ranked}

    def get_claim_requirements(self, asset_id: Optional[str] = None) -> dict[str, Any]:
        asset = next((a for a in self.manifest.get("assets", []) if a.get("id") == asset_id), None)
        asset_type = (asset or {}).get("type", "other")
        institution_slug = (asset or {}).get("institution_id")
        institution = institutions_repo_safe(institution_slug)

        required = list((institution or {}).get("required_docs", []) or [])
        if not required:
            for tmpl in _load_claim_requirements().get("generic_templates", {}).values():
                if asset_type in tmpl.get("product_types", []):
                    required = tmpl.get("base_docs", [])
                    break
        claim_docs = (asset or {}).get("claim_documents", [])
        merged = sorted(set(required) | set(claim_docs))
        return {"asset_id": asset_id, "required_docs": merged}

    def get_document_status(self, claim_id: str) -> dict[str, Any]:
        claim = claims_repo.get_claim(claim_id)
        if not claim:
            return {"claim_id": claim_id, "error": "not_found"}
        checklist = claim.get("checklist") or {}
        required = checklist.get("required", [])
        available = checklist.get("available", [])
        missing = [d for d in required if d not in available]
        return {"claim_id": claim_id, "required": required, "available": available, "missing": missing}

    def create_or_update_claim(self, asset_id: str, status: Optional[str] = None, note: Optional[str] = None) -> dict[str, Any]:
        existing = [c for c in claims_repo.list_claims(vault_id=self.vault_id, nominee_id=self.nominee_id) if c.get("asset_id") == asset_id]
        if existing:
            claim = existing[0]
            if status:
                claims_repo.update_claim(claim["id"], {"status": status})
                claims_repo.add_claim_event(claim["id"], status, note=note)
        else:
            asset = next((a for a in self.manifest.get("assets", []) if a.get("id") == asset_id), None)
            required = self.get_claim_requirements(asset_id).get("required_docs", [])
            claim = claims_repo.create_claim(
                self.vault_id,
                self.nominee_id,
                {"asset_id": asset_id, "institution_id": (asset or {}).get("institution_id"), "status": status or "not_started", "checklist": {"required": required, "available": []}},
            )
            claims_repo.add_claim_event(claim["id"], claim["status"], note=note)
        return {"claim": claim}

    def generate_claim_pack(self, claim_id: str) -> dict[str, Any]:
        claim = claims_repo.get_claim(claim_id)
        if not claim:
            return {"error": "claim_not_found"}
        asset = next((a for a in self.manifest.get("assets", []) if a.get("id") == claim.get("asset_id")), {"label": "Asset"})
        institution = institutions_repo_safe(claim.get("institution_id"))
        checklist_data = claim.get("checklist") or {}
        required = checklist_data.get("required", [])
        available = set(checklist_data.get("available", []))
        checklist = [{"name": d, "present": d in available} for d in required]

        from app.services.pdf.claim_pack import build_claim_pack_pdf

        pdf_bytes = build_claim_pack_pdf(claim=claim, asset=asset, institution=institution, checklist=checklist)
        return {"claim_id": claim_id, "pdf_size_bytes": len(pdf_bytes), "note": "Use POST /claims/{id}/pack to get a signed download URL."}

    def get_sla_status(self, claim_id: str) -> dict[str, Any]:
        claim = claims_repo.get_claim(claim_id)
        if not claim:
            return {"claim_id": claim_id, "error": "not_found"}
        return {"claim_id": claim_id, "status": claim.get("status"), "sla_due_at": claim.get("sla_due_at"), "filed_at": claim.get("filed_at")}

    def draft_escalation(self, claim_id: str, level: str = "gro") -> dict[str, Any]:
        events = claims_repo.list_claim_events(claim_id)
        return {"claim_id": claim_id, "level": level, "event_count": len(events), "note": "Use POST /claims/{id}/escalation for the full drafted letter."}

    def explain_term(self, term: str) -> dict[str, Any]:
        glossary = {
            "nominee": "The person named to RECEIVE the money first. They may hold it in trust for the legal heirs.",
            "legal heir": "Someone entitled to a deceased person's property under succession law -- not always the same as the nominee.",
            "transmission": "The process of transferring mutual fund/security ownership to a claimant after the holder's death.",
            "sum assured": "The guaranteed amount an insurer pays out on a valid claim (before bonuses, if any).",
            "grievance officer": "The institution's internal contact for escalating an unresolved complaint.",
        }
        key = term.strip().lower()
        return {"term": term, "definition": glossary.get(key, "I don't have a plain-language definition for that term yet -- please ask your claim co-pilot for details, or consult the policy document.")}


def institutions_repo_safe(slug: Optional[str]) -> Optional[dict[str, Any]]:
    if not slug:
        return None
    try:
        return institutions_repo.get_institution(slug)
    except Exception:
        return None


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {"type": "function", "function": {"name": "get_asset_map", "description": "Returns the released manifest's asset summary.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_claim_plan", "description": "Returns ranked claims with priority reasons.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_claim_requirements", "description": "Checklist of required documents for an asset's claim.", "parameters": {"type": "object", "properties": {"asset_id": {"type": "string"}}, "required": ["asset_id"]}}},
    {"type": "function", "function": {"name": "get_document_status", "description": "Which documents are present or missing for a claim.", "parameters": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}}},
    {"type": "function", "function": {"name": "create_or_update_claim", "description": "Creates or updates a claim's status/note.", "parameters": {"type": "object", "properties": {"asset_id": {"type": "string"}, "status": {"type": "string"}, "note": {"type": "string"}}, "required": ["asset_id"]}}},
    {"type": "function", "function": {"name": "generate_claim_pack", "description": "Generates the claim-pack PDF for a claim.", "parameters": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}}},
    {"type": "function", "function": {"name": "get_sla_status", "description": "Days elapsed/due for a claim.", "parameters": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}}},
    {"type": "function", "function": {"name": "draft_escalation", "description": "Drafts a grievance/escalation letter for a claim.", "parameters": {"type": "object", "properties": {"claim_id": {"type": "string"}, "level": {"type": "string"}}, "required": ["claim_id"]}}},
    {"type": "function", "function": {"name": "explain_term", "description": "Plain-language definition of a financial/legal term.", "parameters": {"type": "object", "properties": {"term": {"type": "string"}}, "required": ["term"]}}},
]
