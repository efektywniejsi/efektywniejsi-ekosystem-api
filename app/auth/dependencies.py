from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.core import security
from app.db.session import get_db

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization header with Bearer token
        db: Database session

    Returns:
        User model instance

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extract and decode token
    token = credentials.credentials
    payload = security.decode_token(token)

    if payload is None:
        raise credentials_exception

    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID from token
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require admin role.
    Use this for admin-only endpoints.

    Args:
        current_user: Current authenticated user from get_current_user

    Returns:
        User model instance (guaranteed to be admin)

    Raises:
        HTTPException: If user is not an admin

    Example:
        @app.post("/admin/users")
        def create_user(current_user: User = Depends(require_admin)):
            # Only admins can access this
            pass
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
