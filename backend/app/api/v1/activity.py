from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.db.repos import activity as activity_repo
from app.schemas.activity import ActivityIn, ActivityOut

router = APIRouter(tags=["activity"])


@router.post("/activity", response_model=ActivityOut, status_code=201)
async def post_activity(body: ActivityIn, user: CurrentUser = Depends(get_current_user)) -> ActivityOut:
    row = activity_repo.record_activity(user.id, body.kind, body.source, body.meta)
    return ActivityOut.model_validate(row)
