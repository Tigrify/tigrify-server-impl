"""Timestamp and Firestore document serialization helpers."""

from __future__ import annotations

import datetime
from typing import Any, Dict


def now_utc() -> datetime.datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


def now_iso() -> str:
    """Return the current UTC time formatted as an ISO-8601 Z string."""
    return now_utc().isoformat().replace("+00:00", "Z")


def serialize_value(val: Any) -> Any:
    """Recursively convert datetime/date objects inside dicts/lists to ISO strings."""
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: serialize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [serialize_value(v) for v in val]
    return val


def doc_to_dict(doc: Any) -> Dict[str, Any]:
    """Convert a Firestore DocumentSnapshot into a JSON-serializable dict."""
    data = doc.to_dict() or {}
    res = serialize_value(data)
    if "id" not in res and getattr(doc, "id", None):
        res["id"] = doc.id
    return res
