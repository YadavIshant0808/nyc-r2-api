from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.clerk_auth import get_current_user_claims
from app.core.config import settings
from app.schemas.memory import AnalysisResult, ApiError
from app.services.memory_extractor import (
    VertexExtractionError,
    extract_memories_from_audio,
)

router = APIRouter(tags=["audio-analysis"])

_VERTEX_ERROR_STATUS: dict[str, int] = {
    "unsupported_audio_format": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "vertex_not_configured": status.HTTP_503_SERVICE_UNAVAILABLE,
    "vertex_auth_missing": status.HTTP_503_SERVICE_UNAVAILABLE,
    "vertex_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
    "vertex_client_error": status.HTTP_502_BAD_GATEWAY,
    "vertex_api_error": status.HTTP_502_BAD_GATEWAY,
    "empty_model_response": status.HTTP_502_BAD_GATEWAY,
    "invalid_model_output": status.HTTP_502_BAD_GATEWAY,
}


def _upload_error(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ApiError(
            code=code,
            message=message,
            request_id=request_id,
            retryable=False,
        ).model_dump(),
    )


async def _read_audio_upload(
    file: UploadFile,
    request_id: str,
) -> tuple[bytes, str]:
    if file.content_type is None:
        raise _upload_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="missing_content_type",
            message="Uploaded audio is missing a Content-Type.",
            request_id=request_id,
        )

    content_type = file.content_type
    try:
        audio_bytes = await file.read(settings.max_audio_bytes + 1)
    finally:
        await file.close()

    if not audio_bytes:
        raise _upload_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="empty_audio",
            message="Uploaded audio file is empty.",
            request_id=request_id,
        )
    if len(audio_bytes) > settings.max_audio_bytes:
        raise _upload_error(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code="audio_too_large",
            message=f"Audio exceeds the {settings.max_audio_bytes} byte limit.",
            request_id=request_id,
        )

    return audio_bytes, content_type


@router.post("/api/memories/analyze", response_model=AnalysisResult)
async def analyze_audio(
    file: UploadFile = File(...),
    _claims: dict = Depends(get_current_user_claims),
) -> AnalysisResult:
    """Transcribe one audio upload and return review-only candidates."""
    request_id = str(uuid.uuid4())
    audio_bytes, content_type = await _read_audio_upload(file, request_id)

    try:
        return await extract_memories_from_audio(
            audio_bytes=audio_bytes,
            mime_type=content_type,
            request_id=request_id,
        )
    except VertexExtractionError as exc:
        raise HTTPException(
            status_code=_VERTEX_ERROR_STATUS.get(
                exc.code,
                status.HTTP_502_BAD_GATEWAY,
            ),
            detail=ApiError(
                code=exc.code,
                message=exc.message,
                request_id=request_id,
                retryable=exc.retryable,
            ).model_dump(),
        ) from exc
