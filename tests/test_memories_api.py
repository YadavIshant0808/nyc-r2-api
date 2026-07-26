from fastapi.testclient import TestClient

from app.core.config import settings
from app.schemas.memory import AnalysisResult, MemoryCandidate, MemoryKind
from app.services.memory_extractor import VertexExtractionError


def _analysis_result() -> AnalysisResult:
    transcript = "I will send the proposal to Nina tomorrow."
    evidence = "send the proposal to Nina tomorrow"
    start = transcript.index(evidence)
    return AnalysisResult(
        request_id="req-test",
        transcript=transcript,
        summary="A proposal was promised to Nina.",
        detected_language="en",
        candidates=[
            MemoryCandidate(
                client_key="c1",
                kind=MemoryKind.PROMISE,
                title="Send the proposal to Nina",
                owner=None,
                related_person="Nina",
                due_at=None,
                evidence=evidence,
                source_start=start,
                source_end=start + len(evidence),
                confidence=0.98,
                needs_review=False,
            )
        ],
    )


def test_only_audio_memory_route_is_registered(authenticated_app) -> None:
    paths = authenticated_app.openapi()["paths"]

    assert "/api/memories/analyze" in paths
    assert "/api/memories" not in paths
    assert "/api/memories/{memory_id}" not in paths


def test_analyze_accepts_frontend_file_field(
    authenticated_app,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_extract_memories_from_audio(**kwargs):
        captured.update(kwargs)
        return _analysis_result()

    monkeypatch.setattr(
        "app.routers.audio_analysis.extract_memories_from_audio",
        fake_extract_memories_from_audio,
    )

    with TestClient(authenticated_app) as client:
        response = client.post(
            "/api/memories/analyze",
            files={"file": ("memo.wav", b"RIFF-test-audio", "audio/wav")},
            data={"source_type": "audio"},
        )

    assert response.status_code == 200
    assert response.json()["candidates"][0]["kind"] == "promise"
    assert captured["audio_bytes"] == b"RIFF-test-audio"
    assert captured["mime_type"] == "audio/wav"


def test_analyze_rejects_non_audio_upload(authenticated_app) -> None:
    with TestClient(authenticated_app) as client:
        response = client.post(
            "/api/memories/analyze",
            files={"file": ("memo.txt", b"not audio", "text/plain")},
        )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_audio_format"


def test_analyze_maps_vertex_failure_to_public_error(
    authenticated_app,
    monkeypatch,
) -> None:
    async def fake_extract_memories_from_audio(**_kwargs):
        raise VertexExtractionError(
            code="vertex_unavailable",
            message="Vertex AI is temporarily unavailable.",
            retryable=True,
        )

    monkeypatch.setattr(
        "app.routers.audio_analysis.extract_memories_from_audio",
        fake_extract_memories_from_audio,
    )

    with TestClient(authenticated_app) as client:
        response = client.post(
            "/api/memories/analyze",
            files={"file": ("memo.wav", b"RIFF-test-audio", "audio/wav")},
        )

    assert response.status_code == 503
    assert response.json()["detail"]["retryable"] is True


def test_analyze_rejects_empty_audio(authenticated_app) -> None:
    with TestClient(authenticated_app) as client:
        response = client.post(
            "/api/memories/analyze",
            files={"file": ("memo.wav", b"", "audio/wav")},
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "empty_audio"


def test_analyze_rejects_oversized_audio(
    authenticated_app,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "max_audio_bytes", 3)

    with TestClient(authenticated_app) as client:
        response = client.post(
            "/api/memories/analyze",
            files={"file": ("memo.wav", b"1234", "audio/wav")},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "audio_too_large"


def test_analyze_requires_authentication(authenticated_app) -> None:
    authenticated_app.dependency_overrides.clear()
    with TestClient(authenticated_app) as client:
        response = client.post(
            "/api/memories/analyze",
            files={"file": ("memo.wav", b"RIFF", "audio/wav")},
        )

    assert response.status_code == 401
