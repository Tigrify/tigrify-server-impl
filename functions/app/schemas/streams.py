"""Stream request schemas."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class StreamAddRequest(BaseModel):
    title: str
    category: Optional[str] = "General"
    status: Optional[str] = "active"
    creatorId: Optional[str] = "ADMIN"
    creatorName: Optional[str] = "Administrator"
    viewerCount: Optional[int] = 0


class StreamUpdateRequest(BaseModel):
    id: str
    title: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    viewerCount: Optional[int] = None


class StreamDeleteRequest(BaseModel):
    id: str
