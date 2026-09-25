from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.db.repos import profiles as profiles_repo
from app.schemas.me import ConsentIn, ConsentOut, ProfileOut, ProfilePatch

router = APIRouter(tags=["me"])


@router.get("/me", response_model=ProfileOut)
async def get_me(user: CurrentUser = Depends(get_current_user)) -> ProfileOut:
    profile = profiles_repo.get_profile(user.id) or {"id": user.id, "email": user.email}
    return ProfileOut.model_validate({"roles": [], **profile})


@router.patch("/me", response_model=ProfileOut)
async def patch_me(patch: ProfilePatch, user: CurrentUser = Depends(get_current_user)) -> ProfileOut:
    profile = profiles_repo.update_profile(user.id, patch.model_dump(exclude_unset=True))
    return ProfileOut.model_validate({"roles": [], **profile})


@router.post("/me/consents", response_model=ConsentOut, status_code=201)
async def post_consent(body: ConsentIn, user: CurrentUser = Depends(get_current_user)) -> ConsentOut:
    row = profiles_repo.add_consent(user.id, body.purpose, body.version)
    return ConsentOut.model_validate(row)
