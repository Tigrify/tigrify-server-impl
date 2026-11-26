"""Unit tests for LessonService validation, placement increments, and seeding."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import HTTPException

from app.schemas.lessons import LessonAddRequest, LessonUpdateRequest
from app.services.lesson_service import LessonService


class _FakeLessonRepo:
    def __init__(self):
        self.lessons = {}
        self.next_placement = 1

    def create_with_auto_placement(self, build_lesson):
        lid = f"lesson-{self.next_placement}"
        data = build_lesson(lid, self.next_placement)
        self.next_placement += 1
        self.lessons[lid] = dict(data)
        return dict(data)

    def list_ordered(self):
        return sorted(self.lessons.values(), key=lambda x: x["placement"])

    def get_or_404(self, lid: str):
        if lid not in self.lessons:
            raise HTTPException(status_code=404, detail=f"Lesson {lid} not found.")
        return dict(self.lessons[lid])

    def update_or_404(self, lid: str, updates: dict):
        if lid not in self.lessons:
            raise HTTPException(status_code=404, detail=f"Lesson {lid} not found.")
        self.lessons[lid].update(updates)
        return dict(self.lessons[lid])

    def delete_or_404(self, lid: str):
        if lid not in self.lessons:
            raise HTTPException(status_code=404, detail=f"Lesson {lid} not found.")
        del self.lessons[lid]


class TestLessonService(unittest.TestCase):
    def setUp(self):
        self.repo = _FakeLessonRepo()
        self.service = LessonService(self.repo)

    def test_add_seed_filter_update_and_delete(self):
        first = self.service.add_lesson(
            LessonAddRequest(type=2, prompt="Q1", chapter="Basics", section="A", difficulty=1, content={"answer": "hi"})
        )
        self.assertEqual(first["lesson"]["placement"], 1)

        seeded = self.service.seed_default_lesson()
        self.assertEqual(seeded["lesson"]["placement"], 2)
        self.assertEqual(seeded["lesson"]["chapter"], "Glocery")

        filtered = self.service.list_lessons(chapter="basics", difficulty=1)
        self.assertEqual(filtered["count"], 1)

        updated = self.service.update_lesson(LessonUpdateRequest(lessonid="lesson-1", difficulty=3))
        self.assertEqual(updated["lesson"]["difficulty"], 3)

        self.service.delete_lesson("lesson-1")
        self.assertEqual(self.service.list_lessons()["count"], 1)

    def test_invalid_difficulty_raises_400(self):
        with self.assertRaises(HTTPException) as ctx:
            self.service.add_lesson(
                LessonAddRequest(type=1, prompt="Q", chapter="C", section="S", difficulty=9, content={})
            )
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
