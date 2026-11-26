"""Lazy, fork-safe Firebase Admin initialization and Firestore client access."""

from __future__ import annotations

import os
import traceback

import firebase_admin
from firebase_admin import firestore
from firebase_functions import logger

from app.core.config import DEFAULT_PROJECT_ID

_DB_CLIENT = None
_DB_PID = None


def ensure_firebase_initialized() -> None:
    """Initialize Firebase Admin SDK lazily if not yet initialized in this process."""
    if firebase_admin._apps:
        return

    env_info = {
        "pid": os.getpid(),
        "gcloudProject": os.environ.get("GCLOUD_PROJECT"),
        "googleCloudProject": os.environ.get("GOOGLE_CLOUD_PROJECT"),
        "kService": os.environ.get("K_SERVICE"),
        "functionTarget": os.environ.get("FUNCTION_TARGET"),
        "hasGoogleAppCreds": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")),
        "hasFirebaseConfig": bool(os.environ.get("FIREBASE_CONFIG")),
    }
    try:
        firebase_admin.initialize_app()
        logger.info("firebase_admin.initialize_app() succeeded", **env_info)
    except Exception as init_exc:
        logger.warn(
            "firebase_admin.initialize_app() failed, retrying with explicit projectId",
            errorType=type(init_exc).__name__,
            error=str(init_exc),
            **env_info,
        )
        try:
            firebase_admin.initialize_app(options={"projectId": DEFAULT_PROJECT_ID})
            logger.info(
                "firebase_admin.initialize_app(projectId) succeeded",
                projectId=DEFAULT_PROJECT_ID,
                **env_info,
            )
        except Exception as fallback_exc:
            logger.error(
                "firebase_admin.initialize_app() fallback failed",
                errorType=type(fallback_exc).__name__,
                error=str(fallback_exc),
                traceback=traceback.format_exc(),
                **env_info,
            )
            raise


def get_db():
    """Return a fork-safe Firestore client cached per worker PID."""
    global _DB_CLIENT, _DB_PID
    pid = os.getpid()
    if _DB_CLIENT is not None and _DB_PID == pid:
        return _DB_CLIENT

    ensure_firebase_initialized()
    try:
        client = firestore.client()
    except Exception as client_exc:
        logger.error(
            "firestore.client() initialization failed",
            pid=pid,
            errorType=type(client_exc).__name__,
            error=str(client_exc),
            traceback=traceback.format_exc(),
        )
        raise

    _DB_CLIENT = client
    _DB_PID = pid
    logger.info(
        "Firestore client ready",
        pid=pid,
        project=getattr(client, "project", None),
        database=getattr(client, "_database", "(default)"),
    )
    return _DB_CLIENT
