from __future__ import annotations
from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Define Memory type list to choose
class MemoryKind(str, Enum):
    TASK = "task"
    PROMISE = "promise"
    FOLLOW_UP = "follow-up"
    DECISION = "decision"
    IDEA = "idea"
    FACT = "fact"

# Define Memory status list to choose
class MemoryStatus(str, Enum):
    OPEN = "open"
    COMPLETED = "completed"
    DISMISSED = "dismissed"

class MemoryCandidate(BaseModel):
    '''One extracted memory candidate before the user review it.'''
    model_config = ConfigDict(extra="forbid")

    client_key: str = Field(
        min_length=1, description="The unique identifier key associated for this candidate."
    )

    kind: MemoryKind
    title: str = Field(min_length=2, description="The title of the memory.")
    content: str = Field(..., description="The content of the memory.")
    status: Optional[MemoryStatus] = Field(
        default=MemoryStatus.OPEN,
        description="The status of the memory.",
    )
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="The timestamp when the memory was created.",
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="The timestamp when the memory was last updated.",
    )

    @model_validator(mode="before")
    def validate_content_length(cls, values):
        content = values.get("content")
        if content and len(content) > 500:
            raise ValueError("Content must be 500 characters or less.")
        return values