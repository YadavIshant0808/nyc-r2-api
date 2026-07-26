import pytest
from pydantic import ValidationError

from app.schemas.memory import AnalysisResult, MemoryCandidate, MemoryKind
from app.services.memory_extractor import (
    _normalize_audio_candidate,
    _normalize_mime_type,
)


def _candidate(**overrides) -> MemoryCandidate:
    values = {
        "client_key": "c1",
        "kind": MemoryKind.TASK,
        "title": "Send proposal",
        "owner": None,
        "related_person": "Nina",
        "due_at": None,
        "evidence": "send the proposal",
        "source_start": 7,
        "source_end": 24,
        "confidence": 0.9,
        "needs_review": False,
    }
    values.update(overrides)
    return MemoryCandidate(**values)


def test_analysis_accepts_exact_evidence_offsets() -> None:
    result = AnalysisResult(
        request_id="req-1",
        transcript="I will send the proposal tomorrow.",
        summary="A proposal will be sent.",
        detected_language="en",
        candidates=[_candidate()],
    )

    assert result.candidates[0].evidence == "send the proposal"


def test_analysis_rejects_evidence_not_in_transcript() -> None:
    with pytest.raises(ValidationError, match="evidence must occur"):
        AnalysisResult(
            request_id="req-1",
            transcript="There is no supported commitment here.",
            summary="No commitment.",
            detected_language="en",
            candidates=[
                _candidate(source_start=None, source_end=None),
            ],
        )


def test_candidate_requires_offset_pair() -> None:
    with pytest.raises(ValidationError, match="must be supplied together"):
        _candidate(source_end=None)


def test_browser_codec_parameter_is_removed_from_mime_type() -> None:
    assert _normalize_mime_type("audio/webm;codecs=opus") == "audio/webm"


@pytest.mark.parametrize(
    ("legacy_kind", "expected_kind"),
    [
        (MemoryKind.FACT, MemoryKind.TASK),
        (MemoryKind.FOLLOW_UP, MemoryKind.TASK),
        (MemoryKind.DECISION, MemoryKind.IDEA),
    ],
)
def test_legacy_audio_kind_is_normalized_for_product_folders(
    legacy_kind: MemoryKind,
    expected_kind: MemoryKind,
) -> None:
    candidate = _normalize_audio_candidate(_candidate(kind=legacy_kind))

    assert candidate.kind is expected_kind
    assert candidate.needs_review is True
