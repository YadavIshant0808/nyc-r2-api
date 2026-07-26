from fastapi import APIRouter, Depends

from app.core.clerk_auth import get_current_user_profile

router = APIRouter(tags=["greeting"])


@router.get("/api/greeting")
async def greet(user: dict = Depends(get_current_user_profile)):
    """
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    Returns a greeting using the caller's Clerk profile.
    """
    first_name = user.get("first_name")
    username = user.get("username")
    email = None
    email_addresses = user.get("email_addresses") or []
    if email_addresses:
        email = email_addresses[0].get("email_address")

    display_name = first_name or username or email or "there"

    return {
        "message": f"Hello, {display_name}! 👋",
        "clerk_user_id": user.get("id"),
        "username": username,
        "email": email,
    }
