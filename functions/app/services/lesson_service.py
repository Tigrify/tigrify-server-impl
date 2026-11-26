"""Lesson curriculum validation, placement auto-incrementation, and seeding."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.core.config import VALID_DIFFICULTIES
from app.core.serializers import now_utc
from app.repositories.lesson_repo import LessonRepository
from app.schemas.lessons import LessonAddRequest, LessonUpdateRequest


class LessonService:
    """Service layer for curriculum Lesson CRUD and example seeding."""

    def __init__(self, repo: LessonRepository) -> None:
        self.repo = repo

    def add_lesson(self, payload: LessonAddRequest) -> Dict[str, Any]:
        if payload.difficulty not in VALID_DIFFICULTIES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="difficulty must be 1, 2, or 3.")
        if payload.type < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be >= 0.")

        now = now_utc()

        def build(lesson_id: str, next_placement: int) -> Dict[str, Any]:
            return {
                "lessonid": lesson_id,
                "placement": next_placement,
                "type": payload.type,
                "prompt": payload.prompt,
                "chapter": payload.chapter,
                "section": payload.section,
                "difficulty": payload.difficulty,
                "content": payload.content,
                "createdAt": now,
            }

        created_lesson = self.repo.create_with_auto_placement(build)
        return {
            "status": "success",
            "message": f"Lesson #{created_lesson['placement']} created",
            "lesson": created_lesson,
        }

    def list_lessons(
        self, chapter: Optional[str] = None, difficulty: Optional[int] = None
    ) -> Dict[str, Any]:
        all_lessons = self.repo.list_ordered()
        lessons = []
        for l in all_lessons:
            if chapter and (l.get("chapter") or "").lower() != chapter.lower():
                continue
            if difficulty is not None and l.get("difficulty") != difficulty:
                continue
            lessons.append(l)
        return {"status": "success", "count": len(lessons), "lessons": lessons}

    def get_lesson(self, lessonid: str) -> Dict[str, Any]:
        return {"status": "success", "lesson": self.repo.get_or_404(lessonid)}

    def update_lesson(self, payload: LessonUpdateRequest) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        if payload.type is not None:
            if payload.type < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be >= 0.")
            updates["type"] = payload.type
        if payload.prompt is not None:
            updates["prompt"] = payload.prompt
        if payload.chapter is not None:
            updates["chapter"] = payload.chapter
        if payload.section is not None:
            updates["section"] = payload.section
        if payload.difficulty is not None:
            if payload.difficulty not in VALID_DIFFICULTIES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="difficulty must be 1, 2, or 3.")
            updates["difficulty"] = payload.difficulty
        if payload.content is not None:
            updates["content"] = payload.content
        if payload.placement is not None:
            if payload.placement < 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="placement must be >= 1.")
            updates["placement"] = payload.placement

        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update.")

        updated = self.repo.update_or_404(payload.lessonid, updates)
        return {"status": "success", "message": "Lesson updated", "lesson": updated}

    def delete_lesson(self, lessonid: str) -> Dict[str, Any]:
        self.repo.delete_or_404(lessonid)
        return {"status": "success", "message": f"Lesson {lessonid} deleted."}

    def seed_default_lesson(self) -> Dict[str, Any]:
        example = LessonAddRequest(
            type=2,
            prompt="Select the correct meaning",
            chapter="Glocery",
            section="Practice",
            difficulty=1,
            content={
                "audio": "https://www.geezexperience.com/sound/7/29407.mp3",
                "choices": ["silver", "stripe", "spot"],
                "answer": "spotted",
                "translation": "ማክያ",
            },
        )
        return self.add_lesson(example)
