"""Stream chat message endpoints (/api/message/*)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from app.core.firebase import get_db
from app.core.security import require_activated, require_student_or_admin
from app.repositories.message_repo import MessageRepository
from app.schemas.messages import MessageAddRequest, MessageDeleteRequest
from app.services.stream_service import MessageService

router = APIRouter()


def get_message_service(db: Any = Depends(get_db)) -> MessageService:
    return MessageService(MessageRepository(db))


@router.post("/message/add", tags=["Messages"], summary="Send a Message in Stream (Student or Admin)")
@router.post("/messages", tags=["Messages"], include_in_schema=False)
def add_message(
    payload: MessageAddRequest,
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: MessageService = Depends(get_message_service),
):
    return service.add_message(payload, ctx)


@router.get("/message/list", tags=["Messages"], summary="List Messages for a Stream (Student or Admin)")
@router.get("/messages", tags=["Messages"], include_in_schema=False)
def list_messages(
    streamId: str = Query(..., description="ID of the stream"),
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: MessageService = Depends(get_message_service),
):
    return service.list_messages(streamId)


@router.post("/message/delete", tags=["Messages"], summary="Delete a Message (Owner or Admin)")
def delete_message(
    payload: MessageDeleteRequest,
    ctx: Dict[str, Any] = Depends(require_activated),
    service: MessageService = Depends(get_message_service),
):
    return service.delete_message(payload.id, ctx)
