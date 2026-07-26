from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from app.core.clerk_auth import get_current_user_profile
from app.core.database import get_db
from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryRead, MemoryStatus
from app.services.memory_validation import apply_memory_update, build_memory_row


router = APIRouter(tags=["memories"])

def _current_user_id(user: dict) -> str:
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
    return user_id


async def _get_owned_memory_or_404(db: AsyncSession, memory_id: int, user_id: str) -> Memory:
    memory = await db.get(Memory, memory_id)
    if memory is None or memory.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return memory


@router.post("/api/memories", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreate,
    user: dict = Depends(get_current_user_profile),
    db: AsyncSession = Depends(get_db),
):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    user_id = _current_user_id(user)

    existing = await db.execute(
        select(Memory).where(Memory.user_id == user_id, Memory.client_key == payload.client_key)
    )
    existing_memory = existing.scalar_one_or_none()
    if existing_memory is not None:
        return existing_memory

    memory = build_memory_row(user_id=user_id, payload=payload)
    db.add(memory)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

        existing = await db.execute(
            select(Memory).where(Memory.user_id == user_id, Memory.client_key == payload.client_key)
        )
        return existing.scalar_one()
    await db.refresh(memory)
    return memory


@router.get("/api/memories", response_model=list[MemoryRead])
async def get_memories(
    user: dict = Depends(get_current_user_profile),
    db: AsyncSession = Depends(get_db),
    status_filter: MemoryStatus | None = None,
    ):
    """Protected route. Requires `Authorization: Bearer <clerk_session_token>`.

    Optional `?status_filter=open|completed|dismissed` narrows the list;
    otherwise returns every memory owned by the caller, newest first.
    """
    user_id = _current_user_id(user)
    query = select(Memory).where(Memory.user_id == user_id)
    if status_filter is not None:
        query = query.where(Memory.status == status_filter)
    query = query.order_by(Memory.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/api/memories/{memory_id}", response_model=MemoryRead)
async def get_memory(
    memory_id: int,
    user: dict = Depends(get_current_user_profile),
    db: AsyncSession = Depends(get_db),
    ):

    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    user_id = _current_user_id(user)
    return await _get_owned_memory_or_404(db, memory_id, user_id)


@router.put("/api/memories/{memory_id}", response_model=MemoryRead)
async def update_memory(
    memory_id: int,
    payload: MemoryUpdate,
    user: dict = Depends(get_current_user_profile),
    db: AsyncSession = Depends(get_db),
    ):
    '''Update the memory'''
    user_id = _current_user_id(user)
    memory = await _get_owned_memory_or_404(db, memory_id, user_id)
    apply_memory_update(memory, payload)
    await db.commit()
    await db.refresh(memory)
    return memory

@router.delete("/api/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: int,
    user: dict = Depends(get_current_user_profile),
    db: AsyncSession = Depends(get_db),
    ):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    user_id = _current_user_id(user)
    memory = await _get_owned_memory_or_404(db, memory_id, user_id)
    await db.delete(memory)
    await db.commit()