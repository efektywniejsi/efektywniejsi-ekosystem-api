"""Celery tasks for AI generation."""

import json
import logging
from typing import Any
from uuid import UUID

from app.ai.models.ai_chat_session import AiChatSession
from app.ai.schemas.ai_generation import AiGenerateRequest, EntityType
from app.ai.services.sales_page_generator import generate_sales_page
from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _save_assistant_response(entity_type: str, entity_id: str, result_dict: dict) -> None:
    """Persist assistant response to the chat session."""
    db = SessionLocal()
    try:
        session = (
            db.query(AiChatSession)
            .filter(
                AiChatSession.entity_type == entity_type,
                AiChatSession.entity_id == UUID(entity_id),
            )
            .first()
        )
        if session:
            assistant_msg = {
                "role": "assistant",
                "content": json.dumps(result_dict.get("sales_page_data", {})),
                "ai_message": result_dict.get("ai_message", ""),
                "sales_page_data": result_dict.get("sales_page_data"),
                "tokens_used": result_dict.get("tokens_used"),
                "model": result_dict.get("model", ""),
            }
            session.messages = [*session.messages, assistant_msg]
            session.pending_response = result_dict
            session.pending_task_id = None
            db.commit()
    except Exception:
        logger.exception("Failed to save assistant response to chat session")
        db.rollback()
    finally:
        db.close()


def _clear_pending_task(entity_type: str, entity_id: str) -> None:
    """Clear pending_task_id on failure."""
    db = SessionLocal()
    try:
        session = (
            db.query(AiChatSession)
            .filter(
                AiChatSession.entity_type == entity_type,
                AiChatSession.entity_id == UUID(entity_id),
            )
            .first()
        )
        if session:
            session.pending_task_id = None
            db.commit()
    except Exception:
        logger.exception("Failed to clear pending task from chat session")
        db.rollback()
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=10)
def generate_sales_page_task(
    self: Any, entity_type: str, entity_id: str, request_data: dict[str, Any]
) -> dict[str, Any]:
    """Run AI sales page generation as a background Celery task."""
    db = SessionLocal()
    try:
        request = AiGenerateRequest(**request_data)
        result = generate_sales_page(db, EntityType(entity_type), UUID(entity_id), request)
        result_dict = result.model_dump()

        # Persist assistant response to chat session
        _save_assistant_response(entity_type, entity_id, result_dict)

        return result_dict
    except Exception as exc:
        logger.exception("AI generation task failed: %s", exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        _clear_pending_task(entity_type, entity_id)
        raise
    finally:
        db.close()
