"""Shared Firestore repository base class eliminating duplicate CRUD boilerplate."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.serializers import doc_to_dict, serialize_value


class BaseFirestoreRepository:
    """Base CRUD wrapper around a single Firestore collection."""

    collection_name: str = ""
    entity_label: str = "Item"

    def __init__(self, db: Any) -> None:
        self.db = db

    def collection(self) -> Any:
        return self.db.collection(self.collection_name)

    def doc_ref(self, doc_id: Optional[str] = None) -> Any:
        return self.collection().document(doc_id) if doc_id else self.collection().document()

    def get_snapshot(self, doc_id: str) -> Any:
        return self.doc_ref(doc_id).get()

    def get_or_404(self, doc_id: str) -> Dict[str, Any]:
        snap = self.get_snapshot(doc_id)
        if not snap.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.entity_label} {doc_id} not found.",
            )
        return doc_to_dict(snap)

    def ensure_exists(self, doc_id: str) -> Any:
        ref = self.doc_ref(doc_id)
        if not ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.entity_label} {doc_id} not found.",
            )
        return ref

    def update_or_404(self, doc_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        ref = self.ensure_exists(doc_id)
        ref.update(updates)
        return doc_to_dict(ref.get())

    def delete_or_404(self, doc_id: str) -> None:
        ref = self.ensure_exists(doc_id)
        ref.delete()

    def create_with_auto_id(self, payload: Dict[str, Any], id_field: str = "id") -> Dict[str, Any]:
        ref = self.doc_ref()
        record = {id_field: ref.id, **payload}
        ref.set(record)
        return serialize_value(record)

    def stream_all(self) -> List[Dict[str, Any]]:
        return [doc_to_dict(doc) for doc in self.collection().stream()]
