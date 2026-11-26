"""Curriculum lesson endpoints (/api/lesson/*)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.core.firebase import get_db
from app.core.security import require_admin, require_student_or_admin
from app.repositories.lesson_repo import LessonRepository
from app.schemas.lessons import LessonAddRequest, LessonDeleteRequest, LessonUpdateRequest
from app.services.lesson_service import LessonService

router = APIRouter()


def get_lesson_service(db: Any = Depends(get_db)) -> LessonService:
    return LessonService(LessonRepository(db))


@router.post("/lesson/add", tags=["Lessons"], summary="Add / Create Lesson (Admin only, auto-placement)")
@router.post("/lessons", tags=["Lessons"], include_in_schema=False)
def add_lesson(
    payload: LessonAddRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: LessonService = Depends(get_lesson_service),
):
    return service.add_lesson(payload)


@router.get("/lesson/list", tags=["Lessons"], summary="List Lessons ordered by placement (Student or Admin)")
@router.get("/lessons", tags=["Lessons"], include_in_schema=False)
def list_lessons(
    chapter: Optional[str] = Query(None, description="Filter by chapter name"),
    difficulty: Optional[int] = Query(None, description="Filter by difficulty level [1, 2, 3]"),
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: LessonService = Depends(get_lesson_service),
):
    return service.list_lessons(chapter=chapter, difficulty=difficulty)


@router.get("/lesson/get", tags=["Lessons"], summary="Get Lesson by lessonid query (Student or Admin)")
def get_lesson_query(
    lessonid: str = Query(..., description="Unique Lesson ID"),
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: LessonService = Depends(get_lesson_service),
):
    return service.get_lesson(lessonid)


@router.get("/lesson/{lessonid}", tags=["Lessons"], summary="Get Lesson by path parameter (Student or Admin)")
def get_lesson_path(
    lessonid: str,
    ctx: Dict[str, Any] = Depends(require_student_or_admin),
    service: LessonService = Depends(get_lesson_service),
):
    return service.get_lesson(lessonid)


@router.post("/lesson/update", tags=["Lessons"], summary="Update Lesson Details (Admin only)")
@router.put("/lesson/update", tags=["Lessons"], include_in_schema=False)
def update_lesson(
    payload: LessonUpdateRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: LessonService = Depends(get_lesson_service),
):
    return service.update_lesson(payload)


@router.put("/lesson/{lessonid}", tags=["Lessons"], include_in_schema=False)
def update_lesson_path(
    lessonid: str,
    payload: LessonUpdateRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: LessonService = Depends(get_lesson_service),
):
    payload.lessonid = lessonid
    return service.update_lesson(payload)


@router.post("/lesson/delete", tags=["Lessons"], summary="Delete a Lesson (Admin only)")
@router.delete("/lesson/delete", tags=["Lessons"], include_in_schema=False)
def delete_lesson(
    payload: LessonDeleteRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: LessonService = Depends(get_lesson_service),
):
    return service.delete_lesson(payload.lessonid)


@router.delete("/lesson/{lessonid}", tags=["Lessons"], include_in_schema=False)
def delete_lesson_path(
    lessonid: str,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: LessonService = Depends(get_lesson_service),
):
    return service.delete_lesson(lessonid)


@router.post("/lesson/seed", tags=["Lessons"], summary="Seed Default Example Lesson (Admin only)")
def seed_lesson(
    ctx: Dict[str, Any] = Depends(require_admin),
    service: LessonService = Depends(get_lesson_service),
):
    return service.seed_default_lesson()
