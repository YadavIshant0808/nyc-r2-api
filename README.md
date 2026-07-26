# HUMAN-02 API

FastAPI backend for HUMAN-02, a system that turns conversations, documents, and notes into reviewable memories.

This repository currently provides the authenticated API foundation: Clerk token verification, async PostgreSQL access, Alembic migrations, health probes, and protected per-user data routes. The full audio/document analysis pipeline is the next backend vertical slice.

## Current status

| Area | Status |
| --- | --- |
| FastAPI application and CORS | Implemented |
| Clerk JWT verification and profile lookup | Implemented |
| Async PostgreSQL connection pool | Implemented |
| Alembic migration setup | Implemented |
| Liveness and database readiness probes | Implemented |
| Protected per-user note routes | Implemented |
| Memory request/response schemas | In progress |
| `POST /api/memories/analyze` | Stubbed, not registered in `app.main` |
| Audio transcription and document extraction | Not implemented |
| Gemini analysis through Vertex AI | Not implemented |
| Memory persistence and CRUD | Stubbed |
| Automated memory tests | Test files exist but are currently empty |

The frontend can already analyze pasted text and TXT/MD content through its own server-side Gemini route. Audio, PDF, and Word uploads are forwarded toward this API, but will not work until the multipart analysis endpoint is implemented and registered.

## Intended processing flow

```mermaid
flowchart LR
    A[Authenticated upload] --> B[Validate one source]
    B --> C{Source type}
    C -->|Audio| D[Transcribe]
    C -->|PDF or DOCX| E[Extract text]
    C -->|TXT or MD| F[Decode text]
    D --> G[Canonical text or Markdown]
    E --> G
    F --> G
    G --> H[Gemini on Vertex AI]
    H --> I[Validate evidence and schema]
    I --> J[Return review candidates]
    J --> K[Persist only user-approved memories]
```

Raw uploads should remain temporary. Durable storage is intended for approved structured memories and their supporting evidence, not the original audio file.

## Technology

- Python 3.12+
- FastAPI and Uvicorn
- SQLAlchemy 2 with `asyncpg`
- PostgreSQL
- Alembic
- Clerk JWT/JWKS authentication
- Pydantic settings and schemas
- Google Gen AI SDK dependency for the planned Gemini integration
- Docker, Cloud Build, and GKE manifests

## Local setup

### 1. Clone and enter the API repository

```bash
git clone git@github.com:nychacksishv-cmd/nyc-r2-api.git
cd nyc-r2-api
```

### 2. Install dependencies with uv

```bash
uv sync
```

### 3. Create the local environment file

PowerShell:

```powershell
Copy-Item .env.example .env
```

Bash:

```bash
cp .env.example .env
```

Set at least:

```dotenv
CLERK_ISSUER=https://your-app-name.clerk.accounts.dev
CLERK_SECRET_KEY=your_clerk_secret_key
CORS_ORIGINS=http://localhost:3000
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

Use the real password directly in `DATABASE_URL`; angle brackets such as `<PASSWORD>` are documentation placeholders and must not be kept.

Never commit `.env` or real credentials.

### 4. Apply database migrations

```bash
uv run alembic upgrade head
```

### 5. Run the API on port 8000

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Useful local URLs:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Liveness: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/health/ready`

## Active endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | Public | Process liveness |
| GET | `/health/ready` | Public | PostgreSQL readiness |
| GET | `/api/greeting` | Clerk bearer token | Fetch the current Clerk profile and return a greeting |
| GET | `/api/users/{user_id}/notes` | Owner only | List the signed-in user's notes |
| POST | `/api/users/{user_id}/notes` | Owner only | Create a note |
| DELETE | `/api/users/{user_id}/notes/{note_id}` | Owner only | Delete an owned note |

Protected requests require:

```http
Authorization: Bearer <clerk_session_token>
```

The trusted Clerk `sub` claim must match `{user_id}` on owner-scoped routes.

## Project structure

```text
app/
├── core/
│   ├── clerk_auth.py
│   ├── config.py
│   └── database.py
├── models/
├── routers/
│   ├── greeting.py
│   ├── health.py
│   ├── memories.py
│   └── user_data.py
├── schemas/
├── services/
└── main.py
alembic/
├── versions/
└── env.py
k8s/
tests/
cloudbuild.yaml
Dockerfile
pyproject.toml
requirements.txt
```

## Database and migrations

The application does not create tables at startup. Apply Alembic migrations before deploying a new API version:

```bash
uv run alembic upgrade head
```

Each API process owns a SQLAlchemy connection pool. With the current defaults, one replica can open up to:

```text
DB_POOL_SIZE + DB_MAX_OVERFLOW
```

Account for all GKE replicas before increasing either value so the combined pool does not exceed the Cloud SQL connection limit.

## Next backend tasks

1. Register the memory router in `app/main.py`.
2. Implement an authenticated multipart `POST /api/memories/analyze`.
3. Enforce one source per request, file size limits, and MIME/extension validation.
4. Transcribe supported audio and extract readable text from supported documents.
5. Normalize every source into one canonical in-memory text/Markdown contract.
6. Call Gemini through Vertex AI and require schema-constrained output.
7. Reject AI evidence that cannot be found in the canonical source.
8. Return review candidates without persisting them automatically.
9. Add transactional persistence for user-approved memories.
10. Add API, validation, authorization, and failure-path tests.

## Deployment files

- `Dockerfile` builds the API container.
- `cloudbuild.yaml` defines the Google Cloud Build workflow.
- `k8s/deployment.yaml` runs the API and Cloud SQL connectivity configuration.
- `k8s/migrate-job.yaml` applies Alembic migrations as a separate deployment step.
- `k8s/backend-service.yaml`, `backend-ingress.yaml`, `hpa.yaml`, and `ksa.yaml` provide the remaining GKE resources.

Keep secrets in the deployment platform's secret manager or Kubernetes Secret resources. Do not place credentials directly in manifests or Git.
