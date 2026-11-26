"""
Tigrify Cloud Functions Backend API Entrypoint.
Exports the HTTP Cloud Function `api` bridging WSGI requests to FastAPI (`app`)
using a lazy, fork-safe ASGIMiddleware wrapper.
"""

from __future__ import annotations

import io
import json
import os
import traceback

from a2wsgi import ASGIMiddleware
from firebase_functions import https_fn, logger, options

from app.factory import create_app

app = create_app()

_WSGI_APP = None
_WSGI_PID = None


def _get_wsgi_app() -> ASGIMiddleware:
    """Create ASGIMiddleware lazily inside the active worker process (fork-safe)."""
    global _WSGI_APP, _WSGI_PID
    pid = os.getpid()
    if _WSGI_APP is None or _WSGI_PID != pid:
        _WSGI_APP = ASGIMiddleware(app)
        _WSGI_PID = pid
    return _WSGI_APP


@https_fn.on_request(memory=options.MemoryOption.MB_512, cpu=1, max_instances=10)
def api(req: https_fn.Request) -> https_fn.Response:
    """Main Firebase HTTP Function serving FastAPI REST routes and Swagger UI."""
    try:
        environ = dict(req.environ)
        body = req.get_data()
        if body is not None:
            environ["wsgi.input"] = io.BytesIO(body)
            environ["CONTENT_LENGTH"] = str(len(body))
        return https_fn.Response.from_app(_get_wsgi_app(), environ)
    except Exception as exc:
        logger.error(
            "Cloud Function ASGI dispatch error",
            method=req.method,
            path=req.path,
            errorType=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return https_fn.Response(
            json.dumps({"detail": f"Internal API error: {type(exc).__name__}: {exc}"}),
            status=500,
            mimetype="application/json",
        )
