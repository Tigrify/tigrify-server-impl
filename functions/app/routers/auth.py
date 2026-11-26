"""Authentication endpoints (/api/auth/*)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.core.firebase import get_db
from app.core.security import bearer_scheme, get_caller_context, verify_token
from app.repositories.user_repo import UserRepository
from app.schemas.auth import AuthLoginRequest, AuthRefreshRequest, AuthRegisterRequest, AuthVerifyStatusRequest
from app.services.auth_service import AuthService

router = APIRouter()


def get_auth_service(db: Any = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post("/auth/register", tags=["Authentication"], summary="Register a new Student account via main.py")
def auth_register(payload: AuthRegisterRequest, service: AuthService = Depends(get_auth_service)):
    return service.register(payload)


@router.post("/auth/login", tags=["Authentication"], summary="Sign In with Email & Password via main.py")
def auth_login(payload: AuthLoginRequest, service: AuthService = Depends(get_auth_service)):
    return service.login(payload)


@router.post("/auth/refresh", tags=["Authentication"], summary="Refresh Firebase ID Token")
def auth_refresh(payload: AuthRefreshRequest, service: AuthService = Depends(get_auth_service)):
    return service.refresh(payload)


@router.get("/auth/me", tags=["Authentication"], summary="Get Current Authenticated User Session")
def auth_me(
    ctx: Dict[str, Any] = Depends(get_caller_context),
    service: AuthService = Depends(get_auth_service),
):
    return service.me(ctx)


@router.post("/auth/verify-email/resend", tags=["Authentication"], summary="Resend Email Verification Link")
def auth_resend_verification(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    decoded: Dict[str, Any] = Depends(verify_token),
    service: AuthService = Depends(get_auth_service),
):
    return service.resend_verification(creds.credentials)


@router.post("/auth/verify-email/status", tags=["Authentication"], summary="Check Activation & Verification Status")
def auth_check_verification_status(
    payload: AuthVerifyStatusRequest,
    decoded: Dict[str, Any] = Depends(verify_token),
    service: AuthService = Depends(get_auth_service),
):
    return service.check_verification_status(payload, decoded)
