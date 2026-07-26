from fastapi import APIRouter, HTTPException, status

from app.core.database import ping_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """
    Liveness probe target. No auth, no DB call - must always be reachable
    so GKE never kills a pod just because the database had a hiccup.
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """
    Readiness probe target - only reports ready once the DB is reachable.
    GKE stops routing traffic to a pod that fails this, without restarting
    it (unlike a failed liveness probe).
    """
    try:
        await ping_db()
    except Exception as exc:  # noqa: BLE001 - deliberately broad for a health check
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not reachable: {exc}",
        ) from exc
    return {"status": "ready"}
