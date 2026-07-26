from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # allows ORM -> Pydantic

    id: int
    user_id: str
    content: str
    created_at: datetime
