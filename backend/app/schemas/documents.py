from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMBase

DocumentKind = Literal["policy", "statement", "death_certificate", "id_proof", "other"]
DocumentStatus = Literal["uploaded", "processing", "extracted", "needs_review", "failed"]


class PolicyNominee(ORMBase):
    name: str
    relation: Optional[str] = None
    share: Optional[float] = None


class PolicyExtraction(ORMBase):
    insurer: Optional[str] = None
    policy_no: Optional[str] = None
    product_type: Optional[str] = None
    sum_assured: Optional[float] = None
    premium: Optional[float] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    maturity_date: Optional[str] = None
    nominees: list[PolicyNominee] = Field(default_factory=list)
    claim_documents: list[str] = Field(default_factory=list)
    exclusions_summary: Optional[str] = None
    page_refs: list[int] = Field(default_factory=list)


class DocumentOut(ORMBase):
    id: str
    owner_id: str
    asset_id: Optional[str] = None
    kind: DocumentKind
    storage_path: str
    sha256: Optional[str] = None
    extracted: Optional[dict] = None
    status: DocumentStatus = "uploaded"
    created_at: Optional[str] = None


class DeathCertificateExtraction(ORMBase):
    deceased_name: Optional[str] = None
    date_of_death: Optional[str] = None
    place: Optional[str] = None
    registration_no: Optional[str] = None
    issuing_authority: Optional[str] = None
    confidence: Optional[float] = None
