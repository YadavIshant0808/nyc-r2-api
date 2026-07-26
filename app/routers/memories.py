from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from app.core.clerk_auth import get_current_user_profile
from app.core.config import settings    
from app.core.database import get_db
from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryRead, MemoryStatus, ApiError
from app.services.memory_validation import apply_memory_update, build_memory_row
from app.services.memory_extractor import ExtractionNotImplementedError, extract_memories_from_audio


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


@router.post("/api/memories/analyze")
async def analyze_memory(user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    pass

@router.post("/api/memories")
async def create_memory(user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    return {
        "message": "Memory created successfully!",
        "clerk_user_id": user.get("id"),
        "username": user.get("username"),
    }

@router.get("/api/memories")
async def get_memories(user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    return {
        "message": "Memories retrieved successfully!",
        "clerk_user_id": user.get("id"),
        "username": user.get("username"),
    }

@router.get("/api/memories/{memory_id}")
async def get_memory(memory_id: str, user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    pass
@router.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    ''' 
    pass

@router.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str, user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    ''' 
    pass