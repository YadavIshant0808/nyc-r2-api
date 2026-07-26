from __future__ import annotations

from typing import Any

from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryStatus, MemoryUpdate


def apply_memory_update(memory: Memory, payload: MemoryUpdate) -> Memory:
    """Apply updates from a MemoryUpdate payload to an existing Memory instance."""
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(memory, field, value)

    return memory


def build_memory_row(payload: MemoryCreate, user_id: str) -> Memory:
    """Build a new Memory instance from a MemoryCreate payload."""

    return Memory(
        user_id=user_id,
        client_key=payload.client_key,
        kind=payload.kind,
        status=MemoryStatus.OPEN,
        title=payload.title,
        owner=payload.owner,
        related_person=payload.related_person,
        due_at=payload.due_at,
        evidence=payload.evidence,
        source_start=payload.source_start,
        source_end=payload.source_end,
        confidence=payload.confidence,
        needs_review=payload.needs_review,
    )
