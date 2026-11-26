"""Stream CRUD endpoints (/api/stream/*)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.core.firebase import get_db
from app.core.security import require_admin, require_student_or_admin
from app.repositories.stream_repo import StreamRepository
from app.schemas.streams import StreamAddRequest, StreamDeleteRequest, StreamUpdateRequest
from app.services.stream_service import StreamService

router = APIRouter()


def get_stream_service(db: Any = Depends(get_db)) -> StreamService:
    return StreamService(StreamRepository(db))


@router.post("/stream/add", tags=["Streams"], summary="Add / Create a Stream (Admin only)")
@router.post("/streams", tags=["Streams"], include_in_schema=False)
def add_stream(
    payload: StreamAddRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: StreamService = Depends(get_stream_service),
):
    return service.add_stream(payload, ctx)


@router.get("/stream/list", tags=["Streams"], summary="List Streams (Student or Admin)")
@router.get("/streams", tags=["Streams"], include_in_schema=False)
def list_streams(
    status_filter: Optional[str] = Query(
        "active", alias="status", description="Filter by status ('active', 'all', 'ended')"
    ),
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: StreamService = Depends(get_stream_service),
):
    return service.list_streams(status_filter)


@router.get("/stream/get", tags=["Streams"], summary="Get Stream Details (Student or Admin)")
def get_stream_query(
    id: str = Query(..., description="Stream ID"),
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: StreamService = Depends(get_stream_service),
):
    return service.get_stream(id)


@router.get("/stream/{id}", tags=["Streams"], include_in_schema=False)
def get_stream_path(
    id: str,
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: StreamService = Depends(get_stream_service),
):
    return service.get_stream(id)


@router.post("/stream/update", tags=["Streams"], summary="Update Stream (Admin only)")
def update_stream(
    payload: StreamUpdateRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: StreamService = Depends(get_stream_service),
):
    return service.update_stream(payload)


@router.post("/stream/delete", tags=["Streams"], summary="Delete Stream (Admin only)")
def delete_stream(
    payload: StreamDeleteRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: StreamService = Depends(get_stream_service),
):
    return service.delete_stream(payload.id)
