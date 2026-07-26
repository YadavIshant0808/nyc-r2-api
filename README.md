# VoiceVora API

FastAPI backend for VoiceVora, an AI memory assistant that turns uploaded
audio into a transcript, summary, and reviewable Tasks, Promises, and Ideas.

The active analysis flow is audio-only. Audio is sent directly to Gemini,
which performs transcription and structured memory extraction in one request.
PDF and Word conversion, approved-memory persistence, and memory CRUD are not
connected to the running application yet.

## Current status

| Area | Status |
| --- | --- |
| FastAPI application and CORS | Working |
| Clerk bearer-token authentication | Working |
| PostgreSQL connection and Alembic | Working |
| Liveness and readiness probes | Working |
| Authenticated audio analysis | Working |
| Gemini through Vertex AI | Working with Application Default Credentials |
| Gemini API-key fallback | Working |
| Evidence and response validation | Working |
| Tasks, Promises, and Ideas | Working |
| Automated tests | 14 passing |
| PDF, DOC, and DOCX extraction | Not implemented |
| Approved-memory persistence | Not connected |
| Memory CRUD router | Present in source, not registered |

## Processing flow

```mermaid
flowchart LR
    A[Authenticated audio upload] --> B[Validate MIME type and 30 MB limit]
    B --> C[Read audio and close upload]
    C --> D[Gemini audio transcription and extraction]
    D --> E[Pydantic structured-output validation]
    E --> F[Normalize to Task, Promise, or Idea]
    F --> G[Verify evidence against transcript]
    G --> H[Return review-only candidates]
```

VoiceVora does not intentionally persist the uploaded audio. The endpoint
reads the upload for the analysis request and closes it immediately afterward.
Only a validated analysis response is returned.

## Technology

- Python 3.12+
- FastAPI and Uvicorn
- Google Gen AI SDK
- Gemini through Vertex AI or a server-side Gemini API key
- Clerk JWT/JWKS authentication
- Pydantic settings and response schemas
- SQLAlchemy 2 with `asyncpg`
- PostgreSQL and Alembic
- Pytest
- Docker, Cloud Build, and Kubernetes manifests

## Local setup

### 1. Clone the repository

```bash
git clone git@github.com:nychacksishv-cmd/nyc-r2-api.git
cd nyc-r2-api
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Create `.env`

PowerShell:

```powershell
Copy-Item .env.example .env
```

Bash:

```bash
cp .env.example .env
```

Configure the application:

```dotenv
CLERK_ISSUER=https://your-app-name.clerk.accounts.dev
CLERK_SECRET_KEY=your_clerk_secret_key
CORS_ORIGINS=http://localhost:3000,https://nyc-r2-web.vercel.app

DATABASE_URL=postgresql://username:password@localhost:5432/database_name

GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL_ID=gemini-2.5-flash

GEMINI_API_KEY=
VERTEX_TIMEOUT_SECONDS=90
VERTEX_RETRY_COUNT=2
MAX_AUDIO_BYTES=31457280
```

Use the real password in `DATABASE_URL`. Values such as `<PASSWORD>` are
documentation placeholders; do not keep the angle brackets.

Never commit `.env` or real credentials.

### 4. Configure Gemini authentication

Vertex AI with Application Default Credentials is the preferred production
path:

```bash
gcloud auth application-default login
gcloud config set project YOUR_GCP_PROJECT_ID
```

Then set `GOOGLE_CLOUD_PROJECT` in `.env`. On GKE, use Workload Identity
instead of a local credentials file.

For local development, the API can fall back to:

```dotenv
GEMINI_API_KEY=your_server_side_key
```

Keep this key only in the backend environment. An OpenRouter key is not a
drop-in replacement because this implementation uses the Google Gen AI SDK
and Google's authentication flow.

### 5. Apply database migrations

```bash
uv run alembic upgrade head
```

The audio endpoint itself does not currently write analysis results to the
database, but the application startup still initializes the database layer.

### 6. Run on port 8000

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Local URLs:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Liveness: `http://localhost:8000/health`
- Database readiness: `http://localhost:8000/health/ready`

## Active endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | Public | Process liveness |
| GET | `/health/ready` | Public | PostgreSQL readiness |
| POST | `/api/memories/analyze` | Clerk bearer token | Transcribe and analyze one audio file |
| GET | `/api/greeting` | Clerk bearer token | Return a Clerk-backed greeting |
| GET | `/api/users/{user_id}/notes` | Owner only | List the user's notes |
| POST | `/api/users/{user_id}/notes` | Owner only | Create a note |
| DELETE | `/api/users/{user_id}/notes/{note_id}` | Owner only | Delete an owned note |

Protected requests require:

```http
Authorization: Bearer <clerk_session_token>
```

## Audio analysis contract

Send `multipart/form-data` to:

```http
POST /api/memories/analyze
```

Required multipart field:

| Field | Type | Description |
| --- | --- | --- |
| `file` | File | One supported audio file, up to 30 MB by default |

Supported audio MIME types:

- WAV
- MP3 and MPEG audio
- AIFF
- AAC
- OGG and Opus
- FLAC
- WebM audio
- MP4 and M4A audio

The response contains:

- `request_id`
- `transcript`
- `summary`
- `detected_language`
- `warnings`
- Up to 12 `candidates`

Each candidate contains its kind, title, owner, related person, due date,
verbatim evidence, transcript offsets, confidence, and review flag.

The public product contract contains only:

- `task`
- `promise`
- `idea`

Legacy model values are normalized defensively: `fact` and `follow-up` become
reviewable Tasks, while `decision` becomes a reviewable Idea. A legacy value
therefore cannot fail an otherwise valid audio analysis.

## Error behavior

The API returns a structured error containing:

```json
{
  "code": "error_code",
  "message": "Human-readable explanation",
  "request_id": "request identifier",
  "retryable": false
}
```

Common response statuses:

- `400` for an empty upload or missing content type
- `401` for a missing or invalid Clerk session
- `413` when the audio exceeds the configured size limit
- `415` for an unsupported audio format
- `502` for an invalid or rejected Gemini response
- `503` when Gemini authentication or the upstream service is unavailable

## Validation and safety

- Authentication is checked before analysis.
- The API reads at most `MAX_AUDIO_BYTES + 1`.
- Gemini output is parsed through Pydantic.
- Candidate evidence must occur verbatim in the transcript.
- Evidence offsets are recalculated from the returned transcript.
- Duplicate candidate keys and invalid timezone-free due dates are rejected.
- Upstream calls have a timeout and bounded retries.
- Raw audio is not written to application storage.

## Tests

Run the complete suite:

```bash
uv run pytest
```

The tests cover authentication, multipart field compatibility, audio
validation, size limits, upstream error mapping, MIME normalization, evidence
validation, and legacy memory-kind normalization.

## Project structure

```text
app/
|-- core/
|   |-- clerk_auth.py
|   |-- config.py
|   `-- database.py
|-- models/
|-- routers/
|   |-- audio_analysis.py
|   |-- greeting.py
|   |-- health.py
|   |-- memories.py
|   `-- user_data.py
|-- schemas/
|   `-- memory.py
|-- services/
|   `-- memory_extractor.py
`-- main.py
alembic/
tests/
k8s/
cloudbuild.yaml
Dockerfile
pyproject.toml
```

`app/routers/memories.py` contains unfinished persistence-oriented routes, but
`app.main` intentionally registers `audio_analysis.py` as the active memory
analysis router.

## Deployment

Deployment files include:

- `Dockerfile`
- `cloudbuild.yaml`
- GKE deployment, service, ingress, HPA, and service-account manifests
- A separate Alembic migration job

Production must provide Clerk, database, CORS, and Gemini configuration through
the deployment platform's secret/configuration system. Do not put credentials
in Git or Kubernetes manifests.

## Remaining backend work

1. Add PDF, DOC, DOCX, RTF, ODT, TXT, and MD conversion.
2. Normalize document and audio sources behind one analysis contract.
3. Accept the user's timezone for relative dates such as “tomorrow at 5 PM.”
4. Add candidate approval, editing, dismissal, and persistence.
5. Register and finish user-scoped memory CRUD routes.
6. Store only approved structured memories and their evidence.
7. Add rate limits, observability, and production integration tests.

## License

Developed for NYC Code Quest Round 2 by Team GET 200.
