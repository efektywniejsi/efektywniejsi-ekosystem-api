from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.auth.schemas.user import UserResponse
from app.auth.services.email_service import build_welcome_email, get_email_service
from app.core import security
from app.db.session import get_db

router = APIRouter()


class CreateUserRequest(BaseModel):
    """Request schema for creating a new user"""

    email: EmailStr
    name: str
    password: str
    role: Literal["paid", "admin"] = "paid"
    send_welcome_email: bool = False


class UpdateUserRequest(BaseModel):
    """Request schema for updating a user"""

    name: str | None = None
    role: Literal["paid", "admin"] | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    """Response schema for listing users"""

    total: int
    users: list[UserResponse]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    """
    Create a new user (admin only).

    - Validates email uniqueness
    - Creates user with hashed password
    - Optionally sends welcome email

    Args:
        request: User creation data
        db: Database session
        current_user: Current admin user

    Returns:
        Created user data

    Raises:
        HTTP 403: If not admin
        HTTP 409: If email already exists
        HTTP 422: If password is too weak
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Validate password strength
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long",
        )

    # Create new user
    new_user = User(
        email=request.email,
        name=request.name,
        hashed_password=security.get_password_hash(request.password),
        role=request.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send welcome email if requested
    if request.send_welcome_email:
        email_service = get_email_service()
        email_message = build_welcome_email(
            name=new_user.name,
            email=new_user.email,
            temp_password=request.password,
        )
        await email_service.send_email(email_message)

    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    role: Literal["paid", "admin"] | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserListResponse:
    """
    List all users with pagination and filtering (admin only).

    Args:
        skip: Number of users to skip (pagination)
        limit: Maximum number of users to return
        role: Optional role filter
        is_active: Optional active status filter
        db: Database session
        current_user: Current admin user

    Returns:
        List of users with total count

    Raises:
        HTTP 403: If not admin
    """
    # Build query
    query = db.query(User)

    # Apply filters
    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Get total count
    total = query.count()

    # Apply pagination
    users = query.offset(skip).limit(limit).all()

    # Convert to response format
    user_responses = [
        UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
        )
        for user in users
    ]

    return UserListResponse(total=total, users=user_responses)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    """
    Update a user (admin only).

    - Can update name, role, and active status
    - Cannot update email or password (use separate endpoints)

    Args:
        user_id: User UUID to update
        request: Fields to update
        db: Database session
        current_user: Current admin user

    Returns:
        Updated user data

    Raises:
        HTTP 403: If not admin
        HTTP 404: If user not found
    """
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields (only if provided)
    if request.name is not None:
        user.name = request.name
    if request.role is not None:
        user.role = request.role
    if request.is_active is not None:
        user.is_active = request.is_active

    # Update timestamp
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
    )
