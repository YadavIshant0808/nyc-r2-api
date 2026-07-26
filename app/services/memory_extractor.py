from __future__ import annotations

from app.schemas.memory import AnalysisResult

class ExtractionNotImplementedError(Exception):
    """Custom exception to indicate that the extraction method is not implemented."""

async def extract_memories_from_audio(audio_bytes: bytes, 
                                      mime_type: str,
                                      request_id: str
                                      ) -> AnalysisResult:
                                      """
                                      Placeholder for future vertext AI Call.

                                      """
                                      raise ExtractionNotImplementedError("Audio extraction is not implemented yet.")