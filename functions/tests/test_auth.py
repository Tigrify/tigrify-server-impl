"""Unit tests for AuthService registration, login, refresh, and status checks."""

from __future__ import annotations

import pathlib
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.schemas.auth import AuthLoginRequest, AuthRefreshRequest, AuthRegisterRequest, AuthVerifyStatusRequest
from app.services.auth_service import AuthService


class _FakeSnap:
    def __init__(self, doc_id: str, data=None):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _FakeDocRef:
    def __init__(self, store: dict, uid: str):
        self._store = store
        self.id = uid

    def set(self, data: dict):
        self._store[self.id] = dict(data)

    def update(self, updates: dict):
        self._store[self.id].update(updates)


class _FakeUserRepo:
    def __init__(self):
        self.users = {}

    def set_user(self, uid: str, user_data: dict):
        self.users[uid] = dict(user_data)

    def get_raw_and_ref(self, uid: str):
        return _FakeDocRef(self.users, uid), _FakeSnap(uid, self.users.get(uid))


class _FakeRestClient:
    def __init__(self):
        self.calls = []

    def get_web_api_key(self) -> str:
        return "fake-api-key"

    def post(self, url: str, payload: dict, form_encoded: bool = False):
        self.calls.append((url, payload, form_encoded))
        if "signInWithPassword" in url:
            return {"idToken": "tok-123", "refreshToken": "ref-123", "expiresIn": "3600"}
        if "sendOobCode" in url:
            return {"email": payload.get("email")}
        return {"id_token": "tok-new", "refresh_token": "ref-new", "expires_in": "3600"}


class _FakeAuthSdk:
    class EmailAlreadyExistsError(Exception):
        pass

    def __init__(self):
        self.email_verified = False

    def create_user(self, email: str, password: str, display_name: str):
        return types.SimpleNamespace(uid="uid-new")

    def verify_id_token(self, token: str):
        return {"uid": "uid-new", "email": "s@example.com", "email_verified": self.email_verified}

    def get_user(self, uid: str):
        return types.SimpleNamespace(uid=uid, email_verified=self.email_verified)


class TestAuthService(unittest.TestCase):
    def setUp(self):
        self.repo = _FakeUserRepo()
        self.rest = _FakeRestClient()
        self.sdk = _FakeAuthSdk()
        self.service = AuthService(self.repo, rest_client=self.rest, auth_sdk=self.sdk)

    def test_register_creates_inactive_student_and_sends_verification(self):
        with patch("app.services.auth_service.ensure_firebase_initialized"):
            res = self.service.register(
                AuthRegisterRequest(fullName="Ada Lovelace", email="ada@example.com", password="password123")
            )
        self.assertEqual(res["status"], "success")
        self.assertFalse(res["activated"])
        self.assertEqual(self.repo.users["uid-new"]["role"], "STUDENT")
        self.assertTrue(any("sendOobCode" in url for url, _, _ in self.rest.calls))

    def test_login_requires_activation_when_unverified(self):
        self.repo.set_user("uid-new", {"uid": "uid-new", "email": "s@example.com", "activated": False, "role": "STUDENT"})
        with patch("app.services.auth_service.ensure_firebase_initialized"):
            res = self.service.login(AuthLoginRequest(email="s@example.com", password="password123"))
        self.assertEqual(res["status"], "verification_required")
        self.assertFalse(res["activated"])

    def test_login_records_history_and_caps_at_500(self):
        self.sdk.email_verified = True
        self.repo.set_user(
            "uid-new",
            {"uid": "uid-new", "email": "s@example.com", "activated": True, "loginHistory": ["t"] * 500},
        )
        with patch("app.services.auth_service.ensure_firebase_initialized"):
            res = self.service.login(AuthLoginRequest(email="s@example.com", password="password123"))
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(self.repo.users["uid-new"]["loginHistory"]), 500)

    def test_refresh_and_verification_status(self):
        refreshed = self.service.refresh(AuthRefreshRequest(refreshToken="ref-1"))
        self.assertEqual(refreshed["idToken"], "tok-new")

        self.sdk.email_verified = True
        self.repo.set_user("uid-new", {"uid": "uid-new", "activated": False})
        with patch("app.services.auth_service.ensure_firebase_initialized"):
            status_res = self.service.check_verification_status(
                AuthVerifyStatusRequest(refreshToken="ref-1"), {"uid": "uid-new"}
            )
        self.assertTrue(status_res["isActivated"])
        self.assertEqual(status_res["idToken"], "tok-new")


if __name__ == "__main__":
    unittest.main()
