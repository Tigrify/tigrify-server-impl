"""Firestore repository for streams."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.serializers import doc_to_dict
from app.repositories.base import BaseFirestoreRepository


class StreamRepository(BaseFirestoreRepository):
    """Data-access layer for the `streams` collection."""

    collection_name = "streams"
    entity_label = "Stream"

    def list_by_status(self, status_filter: Optional[str]) -> List[Dict[str, Any]]:
        query = self.collection()
        if status_filter and status_filter.lower() != "all":
            query = query.where("status", "==", status_filter)
        return [doc_to_dict(doc) for doc in query.stream()]
