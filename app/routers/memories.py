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