from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.db.repos import assets as assets_repo
from app.db.repos import documents as documents_repo
from app.db.repos import profiles as profiles_repo
from app.db.repos import vaults as vaults_repo
from app.schemas.insights import InsightsOut
from app.services.scoring.coverage import compute_coverage_gap
from app.services.scoring.legacy_score import compute_legacy_score, detect_nominee_gaps

router = APIRouter(tags=["insights"])


@router.get("/insights", response_model=InsightsOut)
async def get_insights(user: CurrentUser = Depends(get_current_user)) -> InsightsOut:
    assets = assets_repo.list_assets(user.id)
    documents = documents_repo.list_documents(user.id)
    profile = profiles_repo.get_profile(user.id) or {}
    vault = vaults_repo.get_vault_by_owner(user.id)

    guardians: list[dict] = []
    vault_nominees: list[dict] = []
    threshold = 2
    if vault:
        from app.db.repos import guardians as guardians_repo
        from app.db.repos import nominees as nominees_repo

        guardians = guardians_repo.list_guardians(vault["id"])
        vault_nominees = nominees_repo.list_nominees(vault["id"])
        threshold = vault.get("threshold", 2)

    score = compute_legacy_score(
        assets=assets,
        guardians=guardians,
        documents=documents,
        threshold=threshold,
        annual_income=profile.get("annual_income"),
        contact_updated_at=profile.get("updated_at"),
    )
    gaps = detect_nominee_gaps(assets=assets, vault_nominees=vault_nominees)
    coverage_gap = compute_coverage_gap(assets=assets, annual_income=profile.get("annual_income"))

    explanation = await _explain(score["legacy_score"], gaps, profile.get("language", "en"))

    return InsightsOut.model_validate(
        {
            "legacy_score": score["legacy_score"],
            "breakdown": score["breakdown"],
            "nominee_gaps": gaps,
            "coverage_gap": coverage_gap,
            "explanation": explanation,
        }
    )


async def _explain(score: int, gaps: list[dict], language: str) -> str:
    try:
        from app.services.ai.groq_client import explain_gaps

        return await explain_gaps(score=score, gaps=gaps, language=language)
    except Exception:
        # Deterministic fallback if Groq isn't configured/available.
        if not gaps:
            return "Your Legacy Vault looks in good shape."
        top = gaps[0]
        return f"Your Legacy Score is {score}. The biggest gap: {top.get('title')}."
