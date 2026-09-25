from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.errors import ApiError
from app.core.security import CurrentUser, get_current_user
from app.db.repos import assets as assets_repo
from app.schemas.assets import AssetAskIn, AssetAskOut, AssetCreate, AssetOut, AssetUpdate

router = APIRouter(tags=["assets"])


@router.get("/assets", response_model=list[AssetOut])
async def list_assets(
    type: Optional[str] = Query(default=None), user: CurrentUser = Depends(get_current_user)
) -> list[AssetOut]:
    rows = assets_repo.list_assets(user.id, type)
    return [AssetOut.model_validate(r) for r in rows]


@router.post("/assets", response_model=AssetOut, status_code=201)
async def create_asset(body: AssetCreate, user: CurrentUser = Depends(get_current_user)) -> AssetOut:
    data = body.model_dump(exclude={"account_ref_full"})
    # account_ref_full would be encrypted at rest (Fernet) before storage in a
    # real deployment; the encrypted column isn't part of the API surface.
    row = assets_repo.create_asset(user.id, data)
    return AssetOut.model_validate(row)


@router.get("/assets/{asset_id}", response_model=AssetOut)
async def get_asset(asset_id: str, user: CurrentUser = Depends(get_current_user)) -> AssetOut:
    row = assets_repo.get_asset(user.id, asset_id)
    if not row:
        raise ApiError("asset_not_found", "Not found", "Asset not found.", 404)
    return AssetOut.model_validate(row)


@router.patch("/assets/{asset_id}", response_model=AssetOut)
async def patch_asset(asset_id: str, body: AssetUpdate, user: CurrentUser = Depends(get_current_user)) -> AssetOut:
    row = assets_repo.update_asset(user.id, asset_id, body.model_dump(exclude_unset=True, exclude={"account_ref_full"}))
    if not row:
        raise ApiError("asset_not_found", "Not found", "Asset not found.", 404)
    return AssetOut.model_validate(row)


@router.delete("/assets/{asset_id}", status_code=204, response_model=None)
async def delete_asset(asset_id: str, user: CurrentUser = Depends(get_current_user)) -> None:
    assets_repo.delete_asset(user.id, asset_id)
    return None


@router.post("/assets/{asset_id}/ask", response_model=AssetAskOut)
async def ask_asset(asset_id: str, body: AssetAskIn, user: CurrentUser = Depends(get_current_user)) -> AssetAskOut:
    row = assets_repo.get_asset(user.id, asset_id)
    if not row:
        raise ApiError("asset_not_found", "Not found", "Asset not found.", 404)
    from app.services.ai.qa import answer_policy_question

    result = await answer_policy_question(asset_id=asset_id, question=body.question, owner_id=user.id)
    return AssetAskOut.model_validate(result)
