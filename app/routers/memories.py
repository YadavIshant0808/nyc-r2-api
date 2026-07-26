from __future__ import annotations

from email.mime import audio
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from app.core.clerk_auth import get_current_user_profile
from app.core.config import settings    
from app.core.database import get_db
from app.models.memory import Memory
from app.schemas.memory import AnalysisResult, MemoryCreate, MemoryUpdate, MemoryRead, MemoryStatus, ApiError
from app.services.memory_validation import apply_memory_update, build_memory_row
from app.services.memory_extractor import VertexExtractionError, extract_memories_from_audio


router = APIRouter(tags=["memories"])

_VERTEX_ERROR_STATUS: dict[str, int] = {
    "unsupported_content": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "vertex_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
    "vertex_client_error":status.HTTP_500_INTERNAL_SERVER_ERROR,
    "vertex_api_error": status.HTTP_502_BAD_GATEWAY,
    "empty_model_response": status.HTTP_502_BAD_GATEWAY,
    "invalid_model_output": status.HTTP_502_BAD_GATEWAY
}

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


@router.post("/api/memories/analyze", response_model=AnalysisResult)
async def analyze_memory(
    audio_file: UploadFile = File(...),
    user: dict = Depends(get_current_user_profile),
):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    request_id = str(uuid.uuid4())
 
    if audio.content_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ApiError(
                code="missing_content_type",
                message="Uploaded audio is missing a Content-Type.",
                request_id=request_id,
                retryable=False,
            ).model_dump(),
        )
    audio_bytes = audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ApiError(
                code="empty_audio",
                message="Uploaded audio file is empty.",
                request_id=request_id,
                retryable=False,
            ).model_dump(),
        )
    if len(audio_bytes) > settings.max_audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=ApiError(
                code="audio_too_large",
                message=f"Audio exceeds the {settings.max_audio_bytes} byte limit.",
                request_id=request_id,
                retryable=False,
            ).model_dump(),
        )
 
    try:
        result = await extract_memories_from_audio(
            audio_bytes=audio_bytes,
            mime_type=audio.content_type,
            request_id=request_id,
        )
    except VertexExtractionError as exc:
        raise HTTPException(
            status_code=_VERTEX_ERROR_STATUS.get(exc.code, status.HTTP_502_BAD_GATEWAY),
            detail=ApiError(
                code=exc.code,
                message=exc.message,
                request_id=request_id,
                retryable=exc.retryable,
            ).model_dump(),
        )
 
    return result

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


@router.put("/api/memories/{memory_id}", response_model = MemoryRead)
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