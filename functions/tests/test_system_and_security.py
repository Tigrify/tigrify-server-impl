"""Tests for app factory, OpenAPI contract, RBAC dependencies, and system routes."""

from __future__ import annotations

import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import HTTPException

from app.core.security import get_caller_context, require_activated, require_admin, verify_token
from app.core.serializers import doc_to_dict, serialize_value
from app.factory import create_app
from app.routers import system


class _FakeSnap:
    def __init__(self, doc_id: str, data=None):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _FakeDocRef:
    def __init__(self, doc_id: str, store: dict):
        self.id = doc_id
        self._store = store

    def get(self, timeout=None):
        return _FakeSnap(self.id, self._store.get(self.id))


class _FakeCollection:
    def __init__(self, store: dict):
        self._store = store

    def document(self, doc_id: str):
        return _FakeDocRef(doc_id, self._store)


class _FakeDb:
    def __init__(self, collections: dict):
        self.project = "tigrify-515619"
        self._database = "(default)"
        self._collections = collections

    def collection(self, name: str):
        return _FakeCollection(self._collections.setdefault(name, {}))


class TestSystemAndSecurity(unittest.TestCase):
    def test_openapi_routes_and_order(self):
        app = create_app()
        spec = app.openapi()
        paths = list(spec["paths"].keys())
        self.assertEqual(len(paths), 34)
        self.assertIn("/api/db-test", paths)
        self.assertLess(paths.index("/api/user/stats"), paths.index("/api/user/{uid}"))

    def test_serializers_convert_datetimes(self):
        dt = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
        out = serialize_value({"ts": dt, "nested": [{"d": dt}]})
        self.assertEqual(out["ts"], dt.isoformat())
        self.assertEqual(out["nested"][0]["d"], dt.isoformat())
        snap = _FakeSnap("doc1", {"name": "Alice", "createdAt": dt})
        self.assertEqual(doc_to_dict(snap)["id"], "doc1")

    def test_verify_token_requires_bearer(self):
        with self.assertRaises(HTTPException) as ctx:
            verify_token(None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_rbac_context_and_admin_guard(self):
        db = _FakeDb({"users": {"u1": {"email": "a@example.com", "role": "ADMIN", "activated": True}}})
        ctx = get_caller_context(decoded={"uid": "u1", "email": "a@example.com", "email_verified": False}, db=db)
        self.assertTrue(ctx["is_activated"])
        self.assertEqual(require_admin(require_activated(ctx))["uid"], "u1")

        student_db = _FakeDb({"users": {"u2": {"email": "s@example.com", "role": "STUDENT", "activated": True}}})
        student_ctx = get_caller_context(decoded={"uid": "u2", "email_verified": True}, db=student_db)
        with self.assertRaises(HTTPException) as exc:
            require_admin(require_activated(student_ctx))
        self.assertEqual(exc.exception.status_code, 403)

    def test_system_health_and_db_probe(self):
        self.assertEqual(system.health_check(check_db=False)["status"], "healthy")
        db = _FakeDb({"counters": {"lessons": {"nextPlacement": 4}}})
        res = system.db_test(db=db)
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["database"]["counterExists"])


if __name__ == "__main__":
    unittest.main()
