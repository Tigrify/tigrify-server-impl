"""Unit tests for StreamService, MessageService, and InteractionService."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import HTTPException

from app.schemas.interactions import InteractionAddRequest
from app.schemas.messages import MessageAddRequest
from app.schemas.streams import StreamAddRequest, StreamUpdateRequest
from app.services.stream_service import InteractionService, MessageService, StreamService


class _FakeDocRef:
    def __init__(self, store: dict, doc_id: str):
        self._store = store
        self._id = doc_id

    def delete(self):
        self._store.pop(self._id, None)


class _FakeBaseRepo:
    def __init__(self):
        self.items = {}
        self._seq = 0

    def create_with_auto_id(self, payload: dict, id_field: str = "id"):
        self._seq += 1
        doc_id = f"doc-{self._seq}"
        rec = {id_field: doc_id, **payload}
        self.items[doc_id] = rec
        return dict(rec)

    def list_by_status(self, status_filter):
        vals = list(self.items.values())
        if status_filter and status_filter.lower() != "all":
            vals = [v for v in vals if v.get("status") == status_filter]
        return vals

    def list_for_stream(self, stream_id: str):
        return [v for v in self.items.values() if v.get("streamId") == stream_id]

    def get_or_404(self, doc_id: str):
        if doc_id not in self.items:
            raise HTTPException(status_code=404, detail=f"Item {doc_id} not found.")
        return dict(self.items[doc_id])

    def update_or_404(self, doc_id: str, updates: dict):
        if doc_id not in self.items:
            raise HTTPException(status_code=404, detail=f"Item {doc_id} not found.")
        self.items[doc_id].update(updates)
        return dict(self.items[doc_id])

    def delete_or_404(self, doc_id: str):
        if doc_id not in self.items:
            raise HTTPException(status_code=404, detail=f"Item {doc_id} not found.")
        del self.items[doc_id]

    def doc_ref(self, doc_id: str):
        return _FakeDocRef(self.items, doc_id)


class TestStreamDomainServices(unittest.TestCase):
    def setUp(self):
        self.admin = {"uid": "admin1", "role": "ADMIN", "profile": {"displayName": "Admin"}}
        self.student1 = {"uid": "s1", "role": "STUDENT", "profile": {"displayName": "Student 1"}}
        self.student2 = {"uid": "s2", "role": "STUDENT", "profile": {"displayName": "Student 2"}}

    def test_stream_crud(self):
        svc = StreamService(_FakeBaseRepo())
        created = svc.add_stream(StreamAddRequest(title="Live Class"), self.admin)
        sid = created["stream"]["id"]
        self.assertEqual(svc.list_streams("active")["count"], 1)
        updated = svc.update_stream(StreamUpdateRequest(id=sid, status="ended"))
        self.assertEqual(updated["stream"]["status"], "ended")
        self.assertEqual(svc.list_streams("active")["count"], 0)
        self.assertEqual(svc.list_streams("all")["count"], 1)
        svc.delete_stream(sid)
        self.assertEqual(svc.list_streams("all")["count"], 0)

    def test_message_delete_enforces_owner_or_admin(self):
        svc = MessageService(_FakeBaseRepo())
        msg = svc.add_message(MessageAddRequest(streamId="st1", senderId="ignored", senderName="S1", content="Hello"), self.student1)
        mid = msg["message"]["id"]
        self.assertEqual(svc.list_messages("st1")["count"], 1)

        with self.assertRaises(HTTPException) as ctx:
            svc.delete_message(mid, self.student2)
        self.assertEqual(ctx.exception.status_code, 403)

        svc.delete_message(mid, self.student1)
        self.assertEqual(svc.list_messages("st1")["count"], 0)

    def test_interactions_bind_actor_id_to_caller(self):
        svc = InteractionService(_FakeBaseRepo())
        res = svc.add_interaction(InteractionAddRequest(streamId="st1", actorId="spoof", actorName="S1", type="heart"), self.student1)
        self.assertEqual(res["interaction"]["actorId"], "s1")
        self.assertEqual(svc.list_interactions("st1")["count"], 1)


if __name__ == "__main__":
    unittest.main()
