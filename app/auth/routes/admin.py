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
    email: EmailStr
    name: str
    password: str
    role: Literal["paid", "admin"] = "paid"
    send_welcome_email: bool = False


class UpdateUserRequest(BaseModel):
    name: str | None = None
    role: Literal["paid", "admin"] | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    total: int
    users: list[UserResponse]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email jest już zarejestrowany",
        )

    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hasło musi mieć co najmniej 8 znaków",
        )

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

    if request.send_welcome_email:
        email_service = get_email_service()
        email_message = build_welcome_email(
            name=str(new_user.name),
            email=str(new_user.email),
            temp_password=request.password,
        )
        await email_service.send_email(email_message)

    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        is_active=new_user.is_active,
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
    query = db.query(User)

    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()

    users = query.offset(skip).limit(limit).all()

    user_responses = [
        UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie znaleziony",
        )

    if request.name is not None:
        user.name = request.name
    if request.role is not None:
        user.role = request.role
    if request.is_active is not None:
        user.is_active = request.is_active

    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
    )
