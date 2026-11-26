"""Authentication request schemas."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    fullName: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")


class AuthLoginRequest(BaseModel):
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="Account password")


class AuthRefreshRequest(BaseModel):
    refreshToken: str = Field(..., description="Firebase refresh token")


class AuthVerifyStatusRequest(BaseModel):
    refreshToken: Optional[str] = Field(None, description="Optional refresh token")
