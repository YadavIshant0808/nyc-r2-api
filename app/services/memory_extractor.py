from __future__ import annotations

import asyncio
import json
import logging

import google.auth
from google import genai
from google.auth.exceptions import DefaultCredentialsError
from google.genai import types as genai_types
from google.genai.errors import APIError, ClientError, ServerError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import settings
from app.schemas.memory import AnalysisResult, MemoryCandidate, MemoryKind

logger = logging.getLogger(__name__)


SUPPORTED_AUDIO_MIME_TYPES = frozenset({
    "audio/wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/aiff",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
    "audio/opus",
    "audio/mp4",
    "audio/m4a",
})


class VertexExtractionError(Exception):
    """Custom exception for errors occurring during vertex AI-based memory extraction."""
    def __init__(self, *, code: str, message: str, retryable: bool) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)

class UnsupportedAudioFormatError(VertexExtractionError):
    def __init__(self, mime_type: str) -> None:
        super().__init__(
            code="unsupported_audio_format",
            message=f"'{mime_type}' is not a supported audio format.",
            retryable=False,
        )

class _GeminiExtractionPayload(BaseModel):
    """Internal model for the payload sent to the Gemini API for memory extraction."""
    model_config = ConfigDict(extra="forbid")
 
    transcript: str
    summary: str
    detected_language: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    candidates: list[MemoryCandidate] = Field(default_factory=list, max_length=12)

 
_SYSTEM_INSTRUCTION = """
You are a careful meeting/voice-memo analyst. You are given a short audio
recording. Do two things:
 
1. Transcribe the audio completely and accurately, preserving the original
   spoken language, in the `transcript` field.
2. Extract "memory candidates" - concrete tasks, promises, or ideas stated
   in the recording.
 
Rules for each candidate:
- `kind` must be exactly one of: task, promise, idea.
- `client_key` must be a short string you generate that is unique within
  this response (e.g. "c1", "c2", ...).
- `evidence` must be a verbatim snippet copied from your own transcript
  (1-500 characters) that supports the candidate - never paraphrase it.
- `source_start` / `source_end` are character offsets into `transcript`
  marking exactly where that evidence snippet appears. If you are not
  confident of the exact offsets, omit both (null) rather than guessing -
  do not provide only one of the two.
- `title` is a short (<=240 character) human-readable label - not a copy
  of the evidence.
- `owner` is who is responsible for a task/promise, if stated. `related_person`
  is who else it concerns. Use null for either if the recording doesn't say.
- `due_at` is an ISO 8601 timestamp WITH a timezone offset if a concrete
  date/time is stated or clearly implied; otherwise null. Never invent a
  date that wasn't stated or clearly implied by the recording.
- `confidence` is your own calibrated confidence (0.0-1.0) that this is a
  real, correctly-classified candidate.
- `needs_review` must be true whenever confidence is below about 0.6, the
  evidence is ambiguous, or a date/owner had to be inferred rather than
  stated directly.
- Extract at most 12 candidates. If there are more real candidates than
  that, keep the 12 most important and note the overflow in `warnings`.
 
Also produce:
- `summary`: 1-3 sentence plain-language summary of the recording.
- `detected_language`: a short code/name for the primary spoken language
  (e.g. "en", "es", "hi-en" for mixed Hindi/English).
- `warnings`: short strings for anything notable - inaudible sections,
  overlapping speakers, dropped candidates, low audio quality, etc. Use an
  empty list if there's nothing to flag.
 
If the recording contains no extractable candidates, return an empty
`candidates` list rather than inventing one.""".strip()

_USER_PROMPT = "Transcribe this recording and extract memory candidates from it."

_client: genai.Client | None = None




def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if settings.google_cloud_project:
            try:
                credentials, _ = google.auth.default()
            except DefaultCredentialsError:
                credentials = None
            else:
                _client = genai.Client(
                    vertexai=True,
                    project=settings.google_cloud_project,
                    location=settings.google_cloud_location,
                    credentials=credentials,
                )

        if _client is None and settings.gemini_api_key:
            _client = genai.Client(api_key=settings.gemini_api_key)

        if _client is None:
            raise VertexExtractionError(
                code="vertex_auth_missing",
                message=(
                    "Vertex AI authentication is unavailable. Configure "
                    "Application Default Credentials or GEMINI_API_KEY."
                ),
                retryable=False,
            )
    return _client


def _normalize_mime_type(mime_type: str) -> str:
    """Strip codec parameters, e.g. 'audio/webm;codecs=opus' -> 'audio/webm'."""
    return mime_type.split(";", 1)[0].strip().lower()

async def extract_memories_from_audio(
    *,
    audio_bytes: bytes,
    mime_type: str,
    request_id: str,
) -> AnalysisResult:
    """
    Send one audio clip to Gemini (via Vertex AI) and return a validated
    AnalysisResult.
 
    Retries `settings.vertex_retry_count` additional times on timeouts and
    5xx server errors (transient). 4xx client errors (bad request, auth,
    permanently-exceeded quota) fail immediately - retrying the exact same
    request won't fix those.
    """
    normalized_mime = _normalize_mime_type(mime_type)
    if normalized_mime not in SUPPORTED_AUDIO_MIME_TYPES:
        raise UnsupportedAudioFormatError(mime_type)
 
    client = _get_client()
    audio_part = genai_types.Part.from_bytes(
        data=audio_bytes,
        mime_type=normalized_mime,
    )
    contents = [
        genai_types.Content(
            role="user",
            parts=[audio_part, genai_types.Part(text=_USER_PROMPT)],
        )
    ]
    config = genai_types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=_GeminiExtractionPayload,
        temperature=0.2,
    )
 
    total_attempts = settings.vertex_retry_count + 1
    last_error: Exception | None = None
    response = None
 
    for attempt in range(1, total_attempts + 1):
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=settings.gemini_model_id,
                    contents=contents,
                    config=config,
                ),
                timeout=settings.vertex_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            last_error = exc
            logger.warning(
                "Vertex request timed out after %.1fs (attempt %s/%s, request_id=%s)",
                settings.vertex_timeout_seconds,
                attempt,
                total_attempts,
                request_id,
            )
            continue
        except ServerError as exc:
            last_error = exc
            logger.warning(
                "Vertex server error (attempt %s/%s, request_id=%s): %s",
                attempt,
                total_attempts,
                request_id,
                exc,
            )
            continue
        except ClientError as exc:
            raise VertexExtractionError(
                code="vertex_client_error",
                message=f"Vertex AI rejected the request: {exc}",
                retryable=False,
            ) from exc
        except APIError as exc:
            raise VertexExtractionError(
                code="vertex_api_error",
                message=f"Vertex AI request failed: {exc}",
                retryable=True,
            ) from exc
        else:
            break
 
    if response is None:
        raise VertexExtractionError(
            code="vertex_unavailable",
            message=(
                f"Vertex AI did not respond successfully after {total_attempts} "
                f"attempt(s): {last_error}"
            ),
            retryable=True,
        )
 
    raw_text = response.text
    if not raw_text:
        raise VertexExtractionError(
            code="empty_model_response",
            message="Gemini returned an empty response.",
            retryable=True,
        )
 
    try:
        payload = _GeminiExtractionPayload.model_validate(json.loads(raw_text))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise VertexExtractionError(
            code="invalid_model_output",
            message=f"Gemini's structured output failed schema validation: {exc}",
            retryable=True,
        ) from exc

    normalized_candidates: list[MemoryCandidate] = []
    for candidate in payload.candidates:
        candidate = _normalize_audio_candidate(candidate)

        source_start = payload.transcript.find(candidate.evidence)
        if source_start < 0:
            raise VertexExtractionError(
                code="invalid_model_output",
                message="Candidate evidence was not found in the transcript.",
                retryable=True,
            )
        normalized_candidates.append(candidate.model_copy(update={
            "source_start": source_start,
            "source_end": source_start + len(candidate.evidence),
        }))

    try:
        return AnalysisResult(
            request_id=request_id,
            transcript=payload.transcript,
            summary=payload.summary,
            detected_language=payload.detected_language,
            warnings=payload.warnings,
            candidates=normalized_candidates,
        )
    except ValidationError as exc:
        raise VertexExtractionError(
            code="invalid_model_output",
            message=f"Assembled analysis result failed validation: {exc}",
            retryable=True,
        ) from exc
