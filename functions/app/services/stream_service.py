"""Services for live/recorded streams, chat messages, and stream interactions."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.core.serializers import now_utc
from app.repositories.interaction_repo import InteractionRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.stream_repo import StreamRepository
from app.schemas.interactions import InteractionAddRequest
from app.schemas.messages import MessageAddRequest
from app.schemas.streams import StreamAddRequest, StreamUpdateRequest


class StreamService:
    """Service layer for Stream lifecycle and filtering."""

    def __init__(self, repo: StreamRepository) -> None:
        self.repo = repo

    def add_stream(self, payload: StreamAddRequest, ctx: Dict[str, Any]) -> Dict[str, Any]:
        stream = self.repo.create_with_auto_id(
            {
                "title": payload.title,
                "category": payload.category or "General",
                "status": payload.status or "active",
                "creatorId": ctx["uid"],
                "creatorName": ctx["profile"].get("displayName") or payload.creatorName or "Administrator",
                "viewerCount": payload.viewerCount or 0,
                "createdAt": now_utc(),
            }
        )
        return {"status": "success", "stream": stream}

    def list_streams(self, status_filter: Optional[str]) -> Dict[str, Any]:
        streams = self.repo.list_by_status(status_filter)
        return {"status": "success", "count": len(streams), "streams": streams}

    def get_stream(self, stream_id: str) -> Dict[str, Any]:
        return {"status": "success", "stream": self.repo.get_or_404(stream_id)}

    def update_stream(self, payload: StreamUpdateRequest) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        for field in ("title", "category", "status", "viewerCount"):
            val = getattr(payload, field)
            if val is not None:
                updates[field] = val
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update.")
        updated = self.repo.update_or_404(payload.id, updates)
        return {"status": "success", "stream": updated}

    def delete_stream(self, stream_id: str) -> Dict[str, Any]:
        self.repo.delete_or_404(stream_id)
        return {"status": "success", "message": f"Stream {stream_id} deleted."}


class MessageService:
    """Service layer for stream chat messages."""

    def __init__(self, repo: MessageRepository) -> None:
        self.repo = repo

    def add_message(self, payload: MessageAddRequest, ctx: Dict[str, Any]) -> Dict[str, Any]:
        msg = self.repo.create_with_auto_id(
            {
                "streamId": payload.streamId,
                "senderId": ctx["uid"],
                "senderName": ctx["profile"].get("displayName") or payload.senderName or "User",
                "content": payload.content,
                "createdAt": now_utc(),
            }
        )
        return {"status": "success", "message": msg}

    def list_messages(self, stream_id: str) -> Dict[str, Any]:
        messages = self.repo.list_for_stream(stream_id)
        return {"status": "success", "count": len(messages), "messages": messages}

    def delete_message(self, message_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        msg_data = self.repo.get_or_404(message_id)
        if ctx["role"] != "ADMIN" and msg_data.get("senderId") != ctx["uid"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the sender or an Admin can delete this message.",
            )
        self.repo.doc_ref(message_id).delete()
        return {"status": "success", "message": f"Message {message_id} deleted."}


class InteractionService:
    """Service layer for stream reactions and interactions."""

    def __init__(self, repo: InteractionRepository) -> None:
        self.repo = repo

    def add_interaction(self, payload: InteractionAddRequest, ctx: Dict[str, Any]) -> Dict[str, Any]:
        interaction = self.repo.create_with_auto_id(
            {
                "streamId": payload.streamId,
                "actorId": ctx["uid"],
                "actorName": ctx["profile"].get("displayName") or payload.actorName or "User",
                "type": payload.type,
                "createdAt": now_utc(),
            }
        )
        return {"status": "success", "interaction": interaction}

    def list_interactions(self, stream_id: str) -> Dict[str, Any]:
        interactions = self.repo.list_for_stream(stream_id)
        return {"status": "success", "count": len(interactions), "interactions": interactions}
