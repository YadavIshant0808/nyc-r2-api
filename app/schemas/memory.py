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
    owner: Optional[str] = Field(default=None, max_length=255)
    related_person: Optional[str] = Field(default=None, max_length=255)
    due_at: Optional[datetime] = Field(default=None, description="The due date and time for the memory.")
    evidence: Optional[str] = Field(min_length=2, max_length=500, description="Verbal snipet copied from the transcript that support this candidate.")
    source_start: Optional[int] = Field(default=None, ge=0)
    source_end: Optional[int] = Field(default=None, ge=0)
    needs_review: bool


    @model_validator(mode="after")
    def _check_offsets(self) -> "MemoryCandidate":
        start, end = self.source_start, self.source_end

    
        if start is not None and end is not None:
            if start < 0:
                raise ValueError("source_start must be a non-negative integer.")
           
            if start >= end:
                raise ValueError("source_start must be less than source_end.")
            
        return self
    
    @model_validator(mode="after")
    def _check_due_at_has_tz(self) -> "MemoryCandidate":
        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("due_at must include timezone information")
        return self
 
 
class AnalysisResult(BaseModel):
    """Full result of one transcript analysis run."""
 
    model_config = ConfigDict(extra="forbid")
 
    request_id: str = Field(min_length=1)
    transcript: str
    summary: str
    detected_language: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    candidates: list[MemoryCandidate] = Field(default_factory=list, max_length=12)

          
class ApiError(BaseModel):
    '''Standard public Api error envelope.'''
 
    model_config = ConfigDict(extra="forbid")
 
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    retryable: bool

class MemoryCreate(BaseModel):
    """ 
    Body for POST /api/memories

    Mirrors MemoryCandidate exactly: a save is "the user accepted this
    candidate as-is or with light edits", so the contract stays identical
    rather than drifting into a second, slightly-different shape.
    """
 
    model_config = ConfigDict(extra="forbid")
 
    client_key: str = Field(min_length=1)
    kind: MemoryKind
    title: str = Field(min_length=1, max_length=240)
    owner: Optional[str] = Field(default=None, max_length=255)
    related_person: Optional[str] = Field(default=None, max_length=255)
    due_at: Optional[datetime] = None
    evidence: str = Field(min_length=1, max_length=500)
    source_start: Optional[int] = Field(default=None, ge=0)
    source_end: Optional[int] = Field(default=None, ge=0)
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = False
 
    @model_validator(mode="after")
    def _check_offsets(self) -> "MemoryCreate":
        start, end = self.source_start, self.source_end
        if start is not None and end is not None and start >= end:
            raise ValueError("source_start must be smaller than source_end")
        return self
 
    @model_validator(mode="after")
    def _check_due_at_has_tz(self) -> "MemoryCreate":
        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("due_at must include timezone information")
        return self

class MemoryUpdate(BaseModel):
    """
    Body for PUT /api/memories/{memory_id}

    Every field is optional; only the keys present in the request body are
    applied (see MemoryUpdate.model_fields_set usage in the router). Unknown
    keys are still rejected - this is an edit contract, not a free-form patch.
    """
 
    model_config = ConfigDict(extra="forbid")
 
    kind: Optional[MemoryKind] = None
    status: Optional[MemoryStatus] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=240)
    owner: Optional[str] = Field(default=None, max_length=255)
    related_person: Optional[str] = Field(default=None, max_length=255)
    due_at: Optional[datetime] = None
    needs_review: Optional[bool] = None
 
    @model_validator(mode="after")
    def _check_due_at_has_tz(self) -> "MemoryUpdate":
        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("due_at must include timezone information")
        return self

class MemoryRead(BaseModel):
    """Response shape for persistant memory """
    model_config = ConfigDict(from_attributes=True)  # allows ORM -> Pydantic
 
    id: int
    user_id: str
    client_key: str
    kind: MemoryKind
    status: MemoryStatus
    title: str
    owner: Optional[str]
    related_person: Optional[str]
    due_at: Optional[datetime]
    evidence: str
    source_start: Optional[int]
    source_end: Optional[int]
    confidence: float
    needs_review: bool
    created_at: datetime
    updated_at: datetime
