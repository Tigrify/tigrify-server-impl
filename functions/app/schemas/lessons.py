"""Lesson request schemas."""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel


class LessonAddRequest(BaseModel):
    type: int = 2
    prompt: str
    chapter: str
    section: str
    difficulty: int = 1
    content: Dict[str, Any]


class LessonUpdateRequest(BaseModel):
    lessonid: str
    type: Optional[int] = None
    prompt: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    difficulty: Optional[int] = None
    content: Optional[Dict[str, Any]] = None
    placement: Optional[int] = None


class LessonDeleteRequest(BaseModel):
    lessonid: str
