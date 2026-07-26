"""
Clerk authentication for FastAPI.

How it works:
1. The Next.js frontend gets a session token from Clerk (via `auth().getToken()`
   or the `useAuth()` hook) and sends it as:  Authorization: Bearer <token>
2. This module verifies that token's signature against Clerk's public JWKS
   (no secret key needed for verification itself - it's just RS256 public-key
   crypto), and checks issuer/expiry.
3. Once verified, we know the trusted `sub` (Clerk user id). To get profile
   info (name, username, email) we call the Clerk Backend API using the
   CLERK_SECRET_KEY - this call is what needs the secret key, and it never
   leaves the backend.
"""

from functools import lru_cache
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _jwk_client() -> jwt.PyJWKClient:
    # Clerk exposes a standard JWKS endpoint under the issuer URL.
    # Cached client re-uses/refreshes keys instead of fetching per-request.
    jwks_url = f"{settings.clerk_issuer}/.well-known/jwks.json"
    return jwt.PyJWKClient(jwks_url)


def verify_session_token(token: str) -> dict[str, Any]:
    """Verify a Clerk session JWT and return its decoded claims."""
    try:
        signing_key = _jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},  # Clerk session tokens don't set aud by default
        )
        return claims
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc


async def get_current_user_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency: returns verified JWT claims (fast, no external call)."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    return verify_session_token(credentials.credentials)


async def get_current_user_profile(
    claims: dict[str, Any] = Depends(get_current_user_claims),
) -> dict[str, Any]:
    """
    FastAPI dependency: verified claims + full Clerk profile (name, username,
    email) fetched from the Clerk Backend API. Use this when you need the
    user's display name, e.g. for the greeting route.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"https://api.clerk.com/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch user profile from Clerk",
        )
    return resp.json()


def require_owner(path_param: str = "user_id"):
    """
    Dependency FACTORY that protects a route so only the Clerk user who
    owns the resource can access it.

    FastAPI doesn't have a Flask-style `@login_required` decorator - the
    idiomatic equivalent is a dependency, injected with `Depends(...)`.
    This one compares the verified token's `sub` (the real, trusted Clerk
    user id) against a path parameter (e.g. `/api/users/{user_id}/...`)
    and raises 403 if they don't match, so a signed-in user can never read
    or write someone else's data just by changing the URL.

    Usage:
        @router.get("/api/users/{user_id}/notes")
        async def get_notes(user_id: str, claims: dict = Depends(require_owner())):
            ...

    If your path param has a different name, pass it explicitly:
        Depends(require_owner(path_param="owner_id"))
    """

    async def _dependency(
        request: Request,
        claims: dict[str, Any] = Depends(get_current_user_claims),
    ) -> dict[str, Any]:
        requested_user_id = request.path_params.get(path_param)
        token_user_id = claims.get("sub")
        if not requested_user_id or requested_user_id != token_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own data",
            )
        return claims

    return _dependency
