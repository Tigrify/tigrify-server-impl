"""Firestore repository for lessons and transactional placement counters."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from firebase_admin import firestore

from app.core.serializers import doc_to_dict, serialize_value
from app.repositories.base import BaseFirestoreRepository


class LessonRepository(BaseFirestoreRepository):
    """Data-access layer for `lessons` and `counters/lessons`."""

    collection_name = "lessons"
    entity_label = "Lesson"

    def create_with_auto_placement(
        self, build_lesson: Callable[[str, int], Dict[str, Any]]
    ) -> Dict[str, Any]:
        lesson_ref = self.doc_ref()
        counter_ref = self.db.collection("counters").document("lessons")

        @firestore.transactional
        def insert_in_tx(tx):
            counter_snap = counter_ref.get(transaction=tx)
            next_placement = 1
            if counter_snap.exists:
                val = (counter_snap.to_dict() or {}).get("nextPlacement")
                if isinstance(val, int):
                    next_placement = val

            tx.set(counter_ref, {"nextPlacement": next_placement + 1})
            lesson_data = build_lesson(lesson_ref.id, next_placement)
            tx.set(lesson_ref, lesson_data)
            return lesson_data

        created = insert_in_tx(self.db.transaction())
        return serialize_value(created)

    def list_ordered(self) -> List[Dict[str, Any]]:
        docs = self.collection().order_by("placement").stream()
        return [doc_to_dict(doc) for doc in docs]
