from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.schemas.memory import MemoryKind, MemoryStatus


class Memory(Base):
    __tablename__ = "memories"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "client_key",
            name="unique_memories_user_client_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    client_key: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[MemoryKind] = mapped_column(
        SAEnum(MemoryKind, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )

    status: Mapped[MemoryStatus] = mapped_column(
        SAEnum(MemoryStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=MemoryStatus.OPEN,
        server_default=MemoryStatus.OPEN.value,
    )
 
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
 
    evidence: Mapped[str] = mapped_column(String(500), nullable=False)
    source_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
 
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
 
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
