"""Firestore repository for user profiles."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.serializers import doc_to_dict
from app.repositories.base import BaseFirestoreRepository


class UserRepository(BaseFirestoreRepository):
    """Data-access layer for the `users` collection."""

    collection_name = "users"
    entity_label = "User"

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        docs = self.collection().where("email", "==", email).limit(1).stream()
        for doc in docs:
            return doc_to_dict(doc)
        return None

    def get_raw_and_ref(self, uid: str):
        ref = self.doc_ref(uid)
        snap = ref.get()
        return ref, snap

    def set_user(self, uid: str, user_data: Dict[str, Any]) -> None:
        self.doc_ref(uid).set(user_data)
