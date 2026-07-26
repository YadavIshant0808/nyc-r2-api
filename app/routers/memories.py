from fastapi import APIRouter, Depends

from app.core.clerk_auth import get_current_user_profile

router = APIRouter(tags=["memories"])

@router.post("/api/memories/analyze")
async def analyze_memory(user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    pass

@router.post("/api/memories")
async def create_memory(user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    return {
        "message": "Memory created successfully!",
        "clerk_user_id": user.get("id"),
        "username": user.get("username"),
    }

@router.get("/api/memories")
async def get_memories(user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    return {
        "message": "Memories retrieved successfully!",
        "clerk_user_id": user.get("id"),
        "username": user.get("username"),
    }

@router.get("/api/memories/{memory_id}")
async def get_memory(memory_id: str, user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    '''
    pass
@router.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    ''' 
    pass

@router.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str, user: dict = Depends(get_current_user_profile)):
    '''
    Protected route. Requires `Authorization: Bearer <clerk_session_token>`.
    ''' 
    pass