"""OpenAPI snapshot and client contract guard tests."""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.factory import create_app

CLIENT_REQUIRED_OPERATIONS = {
    "/api/auth/register": {"post"},
    "/api/auth/login": {"post"},
    "/api/auth/refresh": {"post"},
    "/api/auth/me": {"get"},
    "/api/auth/verify-email/resend": {"post"},
    "/api/auth/verify-email/status": {"post"},
    "/api/user/list": {"get"},
    "/api/user/get": {"get"},
    "/api/user/update": {"post"},
    "/api/lesson/list": {"get"},
    "/api/lesson/add": {"post"},
    "/api/lesson/seed": {"post"},
    "/api/lesson/delete": {"post"},
    "/api/health": {"get"},
    "/api/db-test": {"get"},
}


class TestOpenApiContract(unittest.TestCase):
    def test_snapshot_matches_live_openapi(self):
        snapshot_path = pathlib.Path(__file__).resolve().parent.parent / "openapi.snapshot.json"
        expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
        actual = create_app().openapi()
        self.assertEqual(actual, expected)

    def test_client_required_routes_present(self):
        paths = create_app().openapi()["paths"]
        for path, methods in CLIENT_REQUIRED_OPERATIONS.items():
            self.assertIn(path, paths, f"Missing client-required path: {path}")
            available = {m.lower() for m in paths[path].keys()}
            self.assertTrue(
                methods.issubset(available),
                f"Missing methods {methods - available} on {path}",
            )


if __name__ == "__main__":
    unittest.main()
