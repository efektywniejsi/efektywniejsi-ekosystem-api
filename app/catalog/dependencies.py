from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.models.user import User


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require user to have admin role"""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return current_user
