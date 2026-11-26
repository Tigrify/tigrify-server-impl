"""User request schemas."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class UserAddRequest(BaseModel):
    uid: Optional[str] = None
    email: str
    displayName: Optional[str] = "User"
    role: Optional[str] = "STUDENT"
    belongsTo: Optional[str] = "ADMIN"
    activated: Optional[bool] = False


class UserUpdateRequest(BaseModel):
    uid: str
    displayName: Optional[str] = None
    role: Optional[str] = None
    belongsTo: Optional[str] = None
    activated: Optional[bool] = None


class UserSyncRequest(BaseModel):
    uid: Optional[str] = None
    email: Optional[str] = None
    displayName: Optional[str] = "Student"
    isRegistration: Optional[bool] = False


class UserDeleteRequest(BaseModel):
    uid: str
