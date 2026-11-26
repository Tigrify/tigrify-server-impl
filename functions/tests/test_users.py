"""Unit tests for UserService CRUD, RBAC visibility, stats, and sync."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import HTTPException

from app.schemas.users import UserAddRequest, UserSyncRequest, UserUpdateRequest
from app.services.user_service import UserService, authorize_user_read


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

    def get_snapshot(self, uid: str):
        return _FakeSnap(uid, self.users.get(uid))

    def set_user(self, uid: str, user_data: dict):
        self.users[uid] = dict(user_data)

    def stream_all(self):
        return [{"id": k, **v} for k, v in self.users.items()]

    def get_or_404(self, uid: str):
        if uid not in self.users:
            raise HTTPException(status_code=404, detail=f"User {uid} not found.")
        return {"id": uid, **self.users[uid]}

    def find_by_email(self, email: str):
        for uid, data in self.users.items():
            if data.get("email") == email:
                return {"id": uid, **data}
        return None

    def update_or_404(self, uid: str, updates: dict):
        if uid not in self.users:
            raise HTTPException(status_code=404, detail=f"User {uid} not found.")
        self.users[uid].update(updates)
        return {"id": uid, **self.users[uid]}

    def delete_or_404(self, uid: str):
        if uid not in self.users:
            raise HTTPException(status_code=404, detail=f"User {uid} not found.")
        del self.users[uid]

    def get_raw_and_ref(self, uid: str):
        return _FakeDocRef(self.users, uid), self.get_snapshot(uid)


class TestUserService(unittest.TestCase):
    def setUp(self):
        self.repo = _FakeUserRepo()
        self.service = UserService(self.repo)
        self.admin_ctx = {"uid": "admin1", "email": "admin@tigrify.com", "role": "ADMIN", "is_activated": True, "profile": {}}
        self.parent_ctx = {"uid": "p1", "email": "parent@tigrify.com", "role": "PARENT", "is_activated": True, "profile": {}}

    def test_add_update_stats_delete_user(self):
        created = self.service.add_user(
            UserAddRequest(uid="s1", email="s1@example.com", displayName="Kid One", role="STUDENT", belongsTo="parent@tigrify.com", activated=True)
        )
        self.assertEqual(created["user"]["uid"], "s1")
        self.service.add_user(UserAddRequest(uid="p1", email="parent@tigrify.com", role="PARENT", activated=True))

        listed_parent = self.service.list_users(self.parent_ctx)
        self.assertEqual(listed_parent["count"], 1)
        self.assertEqual(listed_parent["users"][0]["uid"], "s1")

        stats = self.service.get_stats()
        self.assertEqual(stats["stats"]["students"], 1)
        self.assertEqual(stats["stats"]["parents"], 1)

        updated = self.service.update_user(UserUpdateRequest(uid="s1", displayName="Kid Updated"))
        self.assertEqual(updated["user"]["displayName"], "Kid Updated")

        self.service.delete_user("s1")
        self.assertNotIn("s1", self.repo.users)

    def test_authorize_user_read_blocks_unrelated_parent(self):
        with self.assertRaises(HTTPException) as ctx:
            authorize_user_read(self.parent_ctx, "other-student", {"role": "STUDENT", "belongsTo": "other@parent.com"})
        self.assertEqual(ctx.exception.status_code, 403)

    def test_sync_creates_new_inactive_student(self):
        res = self.service.sync_user(
            UserSyncRequest(displayName="New Learner"),
            decoded={"uid": "new-u", "email": "new@example.com", "email_verified": False},
        )
        self.assertTrue(res["isNew"])
        self.assertEqual(res["user"]["role"], "STUDENT")
        self.assertFalse(res["user"]["activated"])


if __name__ == "__main__":
    unittest.main()
