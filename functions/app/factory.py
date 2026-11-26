"""FastAPI application factory assembling middleware, OpenAPI docs, and routers."""

from __future__ import annotations

import traceback

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from firebase_functions import logger

from app.core.config import ALLOWED_ORIGINS, TAGS_METADATA
from app.routers import auth, interactions, lessons, messages, streams, system, users


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with all domain routers."""
    app = FastAPI(
        title="Tigrify Backend API",
        description=(
            "Full-featured Backend REST API with Swagger documentation for Tigrify platform. "
            "Eliminates direct client-side database access from JavaScript and securely handles all CRUD "
            "operations for Users, Lessons, Streams, Messages, and Interactions."
        ),
        version="1.0.0",
        openapi_tags=TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def log_unhandled_exceptions(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(
                "Unhandled API exception",
                method=request.method,
                path=str(request.url.path),
                errorType=type(exc).__name__,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"{type(exc).__name__}: {exc}"},
            )

    root_router = APIRouter()
    for sub_router in (
        system.router,
        auth.router,
        users.router,
        lessons.router,
        streams.router,
        messages.router,
        interactions.router,
    ):
        root_router.include_router(sub_router)

    app.include_router(root_router, prefix="/api")
    app.include_router(root_router, include_in_schema=False)
    return app
