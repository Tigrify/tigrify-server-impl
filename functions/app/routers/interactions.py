"""Stream interaction endpoints (/api/interaction/*)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from app.core.firebase import get_db
from app.core.security import require_student_or_admin
from app.repositories.interaction_repo import InteractionRepository
from app.schemas.interactions import InteractionAddRequest
from app.services.stream_service import InteractionService

router = APIRouter()


def get_interaction_service(db: Any = Depends(get_db)) -> InteractionService:
    return InteractionService(InteractionRepository(db))


@router.post("/interaction/add", tags=["Interactions"], summary="Add an Interaction / Reaction (Student or Admin)")
@router.post("/interactions", tags=["Interactions"], include_in_schema=False)
def add_interaction(
    payload: InteractionAddRequest,
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: InteractionService = Depends(get_interaction_service),
):
    return service.add_interaction(payload, ctx)


@router.get("/interaction/list", tags=["Interactions"], summary="List Interactions for a Stream (Student or Admin)")
@router.get("/interactions", tags=["Interactions"], include_in_schema=False)
def list_interactions(
    streamId: str = Query(..., description="ID of the stream"),
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: InteractionService = Depends(get_interaction_service),
):
    return service.list_interactions(streamId)
