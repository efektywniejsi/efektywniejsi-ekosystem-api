"""AI-powered sales page generation endpoints."""

from uuid import UUID

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.models.ai_chat_session import AiChatSession
from app.ai.schemas.ai_generation import (
    AiChatSessionResponse,
    AiGenerateRequest,
    AiTaskCreatedResponse,
    AiTaskStatusResponse,
    EntityType,
)
from app.ai.tasks import generate_sales_page_task
from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.celery_app import celery_app
from app.core.config import settings
from app.courses.models.course import Course
from app.db.session import get_db
from app.packages.models.package import Package

router = APIRouter()


def _check_api_key() -> None:
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Klucz API Anthropic nie jest skonfigurowany. Ustaw ANTHROPIC_API_KEY w .env",
        )


def _get_or_create_session(db: Session, entity_type: EntityType, entity_id: UUID) -> AiChatSession:
    session: AiChatSession | None = (
        db.query(AiChatSession)
        .filter(
            AiChatSession.entity_type == entity_type,
            AiChatSession.entity_id == entity_id,
        )
        .first()
    )
    if not session:
        session = AiChatSession(
            entity_type=entity_type,
            entity_id=entity_id,
            messages=[],
        )
        db.add(session)
        db.flush()
    return session


def _dispatch_task(
    db: Session,
    entity_type: EntityType,
    entity_id: UUID,
    request: AiGenerateRequest,
) -> AiTaskCreatedResponse:
    chat_session = _get_or_create_session(db, entity_type, entity_id)

    # Build chat_history from existing session messages (role + content only)
    chat_history = [{"role": m["role"], "content": m["content"]} for m in chat_session.messages]

    # Append user message to session
    chat_session.messages = [
        *chat_session.messages,
        {"role": "user", "content": request.prompt},
    ]

    # Override chat_history in request with session state
    request_data = request.model_dump()
    request_data["chat_history"] = chat_history

    # Dispatch Celery task
    task = generate_sales_page_task.delay(entity_type, str(entity_id), request_data)

    # Track active task
    chat_session.pending_task_id = task.id
    chat_session.pending_response = None
    db.commit()

    return AiTaskCreatedResponse(task_id=task.id)


# --- Generation endpoints ---


@router.post(
    "/courses/{course_id}/sales-page/ai-generate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AiTaskCreatedResponse,
)
async def ai_generate_course_sales_page(
    course_id: UUID,
    request: AiGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AiTaskCreatedResponse:
    """Dispatch AI sales page generation task for a course (admin only)."""
    _check_api_key()

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kurs nie znaleziony")

    return _dispatch_task(db, EntityType.COURSE, course_id, request)


@router.post(
    "/bundles/{bundle_id}/sales-page/ai-generate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AiTaskCreatedResponse,
)
async def ai_generate_bundle_sales_page(
    bundle_id: UUID,
    request: AiGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AiTaskCreatedResponse:
    """Dispatch AI sales page generation task for a bundle (admin only)."""
    _check_api_key()

    bundle = db.query(Package).filter(Package.id == bundle_id).first()
    if not bundle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bundle nie znaleziony")

    return _dispatch_task(db, EntityType.BUNDLE, bundle_id, request)


# --- Task polling ---


@router.get(
    "/ai-tasks/{task_id}",
    response_model=AiTaskStatusResponse,
)
async def get_ai_task_status(
    task_id: str,
    current_user: User = Depends(require_admin),
) -> AiTaskStatusResponse:
    """Poll the status of an AI generation task (admin only)."""
    result = AsyncResult(task_id, app=celery_app)

    status_map = {
        "PENDING": "pending",
        "STARTED": "processing",
        "SUCCESS": "completed",
        "FAILURE": "failed",
        "RETRY": "processing",
    }
    mapped_status = status_map.get(result.status, "pending")

    return AiTaskStatusResponse(
        task_id=task_id,
        status=mapped_status,
        result=result.result if result.successful() else None,
        error=str(result.result) if result.failed() else None,
    )


# --- Chat session endpoints ---


@router.get(
    "/courses/{course_id}/sales-page/ai-chat",
    response_model=AiChatSessionResponse,
)
async def get_course_ai_chat(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AiChatSessionResponse:
    """Get AI chat session for a course."""
    return _get_chat_response(db, EntityType.COURSE, course_id)


@router.get(
    "/bundles/{bundle_id}/sales-page/ai-chat",
    response_model=AiChatSessionResponse,
)
async def get_bundle_ai_chat(
    bundle_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AiChatSessionResponse:
    """Get AI chat session for a bundle."""
    return _get_chat_response(db, EntityType.BUNDLE, bundle_id)


@router.delete(
    "/courses/{course_id}/sales-page/ai-chat",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_course_ai_chat(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Clear AI chat session for a course."""
    _clear_chat(db, EntityType.COURSE, course_id)


@router.delete(
    "/bundles/{bundle_id}/sales-page/ai-chat",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_bundle_ai_chat(
    bundle_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Clear AI chat session for a bundle."""
    _clear_chat(db, EntityType.BUNDLE, bundle_id)


@router.post(
    "/courses/{course_id}/sales-page/ai-chat/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def dismiss_course_ai_response(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Dismiss (apply/reject) the pending AI response for a course."""
    _dismiss_pending(db, EntityType.COURSE, course_id)


@router.post(
    "/bundles/{bundle_id}/sales-page/ai-chat/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def dismiss_bundle_ai_response(
    bundle_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Dismiss (apply/reject) the pending AI response for a bundle."""
    _dismiss_pending(db, EntityType.BUNDLE, bundle_id)


# --- Helpers ---


def _get_chat_response(
    db: Session, entity_type: EntityType, entity_id: UUID
) -> AiChatSessionResponse:
    session = (
        db.query(AiChatSession)
        .filter(
            AiChatSession.entity_type == entity_type,
            AiChatSession.entity_id == entity_id,
        )
        .first()
    )
    if not session:
        return AiChatSessionResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
            messages=[],
        )
    return AiChatSessionResponse(
        entity_type=session.entity_type,
        entity_id=str(session.entity_id),
        messages=session.messages,
        pending_task_id=session.pending_task_id,
        pending_response=session.pending_response,
    )


def _clear_chat(db: Session, entity_type: EntityType, entity_id: UUID) -> None:
    db.query(AiChatSession).filter(
        AiChatSession.entity_type == entity_type,
        AiChatSession.entity_id == entity_id,
    ).delete()
    db.commit()


def _dismiss_pending(db: Session, entity_type: EntityType, entity_id: UUID) -> None:
    session = (
        db.query(AiChatSession)
        .filter(
            AiChatSession.entity_type == entity_type,
            AiChatSession.entity_id == entity_id,
        )
        .first()
    )
    if session:
        session.pending_response = None
        db.commit()
