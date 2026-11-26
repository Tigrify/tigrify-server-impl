"""Message request schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MessageAddRequest(BaseModel):
    streamId: str
    senderId: str
    senderName: str
    content: str


class MessageDeleteRequest(BaseModel):
    id: str
