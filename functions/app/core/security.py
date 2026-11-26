"""Authentication bearer token verification and RBAC FastAPI dependencies."""

from __future__ import annotations

import traceback
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
from firebase_functions import logger

from app.core.firebase import ensure_firebase_initialized, get_db

bearer_scheme = HTTPBearer(auto_error=False)


def verify_token(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """Verify the Authorization Bearer Firebase ID token and return decoded claims."""
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token.",
        )
    ensure_firebase_initialized()
    try:
        return auth.verify_id_token(creds.credentials)
    except Exception as exc:
        logger.warn("ID token verification failed", errorType=type(exc).__name__, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Firebase ID token: {exc}",
        )


def get_caller_context(
    decoded: Dict[str, Any] = Depends(verify_token),
    db: Any = Depends(get_db),
) -> Dict[str, Any]:
    """Load the caller's Firestore profile and compute activation & role context."""
    uid = decoded["uid"]
    try:
        doc = db.collection("users").document(uid).get()
    except Exception as exc:
        logger.error(
            "Firestore error in get_caller_context",
            uid=uid,
            errorType=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore query failed: {type(exc).__name__}: {exc}",
        )
    profile = doc.to_dict() if doc.exists else {}
    role = (profile or {}).get("role", "STUDENT")
    is_activated = bool(decoded.get("email_verified")) or bool((profile or {}).get("activated") is True)
    return {
        "decoded": decoded,
        "uid": uid,
        "email": decoded.get("email") or (profile or {}).get("email") or "",
        "profile": profile or {},
        "role": role,
        "is_activated": is_activated,
    }


def require_activated(ctx: Dict[str, Any] = Depends(get_caller_context)) -> Dict[str, Any]:
    """Ensure the authenticated user is email-verified or admin-activated."""
    if not ctx["is_activated"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not activated. Please verify your email or ask an admin to activate it.",
        )
    return ctx


def require_admin(ctx: Dict[str, Any] = Depends(require_activated)) -> Dict[str, Any]:
    """Restrict access to activated ADMIN callers."""
    if ctx["role"] != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")
    return ctx


def require_parent_or_admin(ctx: Dict[str, Any] = Depends(require_activated)) -> Dict[str, Any]:
    """Restrict access to activated PARENT or ADMIN callers."""
    if ctx["role"] not in ("PARENT", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parent or Admin privileges required.")
    return ctx


def require_student_or_admin(ctx: Dict[str, Any] = Depends(require_activated)) -> Dict[str, Any]:
    """Restrict access to activated STUDENT or ADMIN callers."""
    if ctx["role"] not in ("STUDENT", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student or Admin privileges required.")
    return ctx
