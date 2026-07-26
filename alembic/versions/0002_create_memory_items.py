"""create memories table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Enum values must exactly match MemoryKind and MemoryStatus in app/schemas/memory.py
_KIND_ENUM = sa.Enum("task", "promise", "idea", name="memorykind")
_STATUS_ENUM = sa.Enum("open", "completed", "dismissed", name="memorystatus")


def upgrade() -> None:
    _KIND_ENUM.create(op.get_bind(), checkfirst=True)
    _STATUS_ENUM.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("client_key", sa.String(length=255), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("task", "promise", "idea", name="memorykind"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("open", "completed", "dismissed", name="memorystatus"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("related_person", sa.String(length=255), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", sa.String(length=500), nullable=False),
        sa.Column("source_start", sa.Integer(), nullable=True),
        sa.Column("source_end", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "client_key", name="unique_memories_user_client_key"),
    )
    op.create_index("ix_memories_user_id", "memories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_memories_user_id", table_name="memories")
    op.drop_table("memories")
    _STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
    _KIND_ENUM.drop(op.get_bind(), checkfirst=True)
