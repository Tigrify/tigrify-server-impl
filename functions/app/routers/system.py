"""System, root info, health, DB probe, and Swagger redirect routes."""

from __future__ import annotations

import traceback
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from firebase_functions import logger

from app.core.firebase import get_db
from app.core.serializers import now_iso

router = APIRouter()


def _probe_db(db: Any) -> Dict[str, Any]:
    snap = db.collection("counters").document("lessons").get(timeout=8.0)
    info = {
        "connected": True,
        "project": getattr(db, "project", None),
        "databaseId": getattr(db, "_database", "(default)"),
        "counterExists": bool(snap.exists),
    }
    logger.info("Firestore DB probe succeeded", **info)
    return info


@router.get("/", tags=["System"])
def root_info():
    return {
        "service": "Tigrify Backend API",
        "status": "online",
        "mode": "production",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/refresh",
            "/api/auth/me",
            "/api/auth/verify-email/resend",
            "/api/auth/verify-email/status",
            "/api/user/add",
            "/api/user/list",
            "/api/user/get",
            "/api/user/update",
            "/api/user/delete",
            "/api/user/sync",
            "/api/user/stats",
            "/api/lesson/add",
            "/api/lesson/list",
            "/api/lesson/get",
            "/api/lesson/update",
            "/api/lesson/delete",
            "/api/lesson/seed",
            "/api/stream/add",
            "/api/stream/list",
            "/api/stream/get",
            "/api/stream/update",
            "/api/stream/delete",
            "/api/message/add",
            "/api/message/list",
            "/api/message/delete",
            "/api/interaction/add",
            "/api/interaction/list",
        ],
    }


@router.get("/health", tags=["System"])
def health_check(check_db: bool = Query(False, description="Set true to test Firestore connectivity")):
    payload: Dict[str, Any] = {"status": "healthy", "mode": "production", "timestamp": now_iso()}
    if not check_db:
        return payload
    try:
        payload["database"] = _probe_db(get_db())
        return payload
    except Exception as exc:
        logger.error(
            "Firestore DB probe failed",
            errorType=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "mode": "production",
                "timestamp": payload["timestamp"],
                "database": {"connected": False},
                "errorType": type(exc).__name__,
                "detail": str(exc),
            },
        )


@router.get("/db-test", tags=["System"], summary="Test Firestore get_db() connectivity")
def db_test(db: Any = Depends(get_db)):
    try:
        return {"status": "ok", "timestamp": now_iso(), "database": _probe_db(db)}
    except Exception as exc:
        logger.error(
            "Firestore /db-test failed",
            errorType=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "timestamp": now_iso(),
                "errorType": type(exc).__name__,
                "detail": str(exc),
            },
        )


@router.get("/api/docs", include_in_schema=False)
def api_docs_redirect():
    return RedirectResponse(url="/docs")


@router.get("/api/openapi.json", include_in_schema=False)
def api_openapi(request: Request):
    return JSONResponse(content=request.app.openapi())
