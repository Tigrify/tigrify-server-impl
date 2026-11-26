"""Firestore repository for stream chat messages."""

from __future__ import annotations

from typing import Any, Dict, List

from app.core.serializers import doc_to_dict
from app.repositories.base import BaseFirestoreRepository


class MessageRepository(BaseFirestoreRepository):
    """Data-access layer for the `messages` collection."""

    collection_name = "messages"
    entity_label = "Message"

    def list_for_stream(self, stream_id: str) -> List[Dict[str, Any]]:
        docs = self.collection().where("streamId", "==", stream_id).order_by("createdAt").stream()
        return [doc_to_dict(doc) for doc in docs]
