"""Interaction request schemas."""

from __future__ import annotations

from pydantic import BaseModel


class InteractionAddRequest(BaseModel):
    streamId: str
    actorId: str
    actorName: str
    type: str
