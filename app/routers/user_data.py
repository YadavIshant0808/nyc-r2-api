"""
Per-user protected resource, now backed by Postgres. Only the Clerk user
identified by `user_id` in the URL can read/write their own notes - anyone
else signed in gets a 403, and unauthenticated requests get a 401.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clerk_auth import require_owner
from app.core.database import get_db
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteRead

router = APIRouter(prefix="/api/users", tags=["user-data"])


@router.get("/{user_id}/notes", response_model=list[NoteRead])
async def list_notes(
    user_id: str,
    claims: dict = Depends(require_owner()),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{user_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    user_id: str,
    payload: NoteCreate,
    claims: dict = Depends(require_owner()),
    db: AsyncSession = Depends(get_db),
):
    note = Note(user_id=user_id, content=payload.content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{user_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    user_id: str,
    note_id: int,
    claims: dict = Depends(require_owner()),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    # Check both existence AND ownership - a valid note_id belonging to a
    # different user must 404, not leak that it exists.
    if note is None or note.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    await db.delete(note)
    await db.commit()
