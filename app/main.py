from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.routers import audio_analysis, greeting, health, user_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing to do - schema is managed by Alembic migrations
    # (see alembic/), not created here. Run `alembic upgrade head` as a
    # migration step before rolling out a new version (see README.md).
    yield
    # Shutdown: cleanly close the DB connection pool.
    await engine.dispose()


app = FastAPI(title="Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(greeting.router)
app.include_router(user_data.router)
app.include_router(audio_analysis.router)
