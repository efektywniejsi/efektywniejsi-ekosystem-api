"""Orchestrator: fetch context -> build prompt -> call AI -> validate response."""

import json
import logging
import re
import uuid
from typing import Any, cast

from anthropic.types import MessageParam
from sqlalchemy.orm import Session, joinedload

from app.ai.models.brand_guidelines import BrandGuidelines
from app.ai.schemas.ai_generation import AiGenerateRequest, AiGenerateResponse, EntityType
from app.ai.services.anthropic_service import call_anthropic
from app.ai.services.brand_guidelines_service import get_brand_guidelines
from app.ai.services.prompt_builder import (
    build_iterative_user_message,
    build_system_prompt,
)
from app.core.config import settings
from app.courses.models.course import Course, Module
from app.courses.schemas.sales_page import SECTION_CONFIG_MAP, SalesPageData
from app.packages.models.package import Package

logger = logging.getLogger(__name__)


def _fetch_course_data(db: Session, course_id: uuid.UUID) -> dict[str, Any]:
    """Fetch course with modules and lessons for AI context."""
    course = (
        db.query(Course)
        .options(joinedload(Course.modules).joinedload(Module.lessons))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise ValueError(f"Course {course_id} not found")

    modules_data = []
    for module in sorted(course.modules, key=lambda m: m.sort_order):
        lessons_data = []
        for lesson in sorted(module.lessons, key=lambda ls: ls.sort_order):
            lessons_data.append(
                {
                    "title": lesson.title,
                    "description": lesson.description,
                    "duration_seconds": lesson.duration_seconds,
                    "is_preview": lesson.is_preview,
                }
            )
        modules_data.append(
            {
                "title": module.title,
                "description": module.description,
                "lessons": lessons_data,
            }
        )

    return {
        "title": course.title,
        "description": course.description,
        "difficulty": course.difficulty,
        "estimated_hours": course.estimated_hours,
        "category": course.category,
        "modules": modules_data,
    }


def _fetch_bundle_data(db: Session, bundle_id: uuid.UUID) -> dict[str, Any]:
    """Fetch bundle with items for AI context."""
    bundle = (
        db.query(Package)
        .options(
            joinedload(Package.bundle_items),
            joinedload(Package.course_items),
        )
        .filter(Package.id == bundle_id)
        .first()
    )
    if not bundle:
        raise ValueError(f"Bundle {bundle_id} not found")

    bundle_items_data = []
    for item in sorted(bundle.bundle_items, key=lambda i: i.sort_order):
        child = item.child_package
        if child:
            bundle_items_data.append(
                {
                    "child_package": {
                        "title": child.title,
                        "description": child.description,
                    }
                }
            )

    course_items_data = []
    for item in sorted(bundle.course_items, key=lambda i: i.sort_order):
        course = item.course
        if course:
            course_items_data.append(
                {
                    "course": {
                        "title": course.title,
                        "description": course.description,
                    }
                }
            )

    return {
        "title": bundle.title,
        "description": bundle.description,
        "price": bundle.price,
        "original_price": bundle.original_price,
        "difficulty": bundle.difficulty,
        "category": bundle.category,
        "bundle_items": bundle_items_data,
        "course_items": course_items_data,
    }


def _fetch_few_shot_examples(
    db: Session,
    entity_type: EntityType,
    exclude_id: uuid.UUID,
    limit: int = 2,
) -> list[dict[str, Any]]:
    """Fetch existing sales pages as few-shot examples."""
    examples: list[dict[str, Any]] = []

    if entity_type == EntityType.COURSE:
        courses = (
            db.query(Course)
            .filter(
                Course.id != exclude_id,
                Course.sales_page_sections.isnot(None),
            )
            .limit(limit)
            .all()
        )
        for course in courses:
            if course.sales_page_sections:
                examples.append(course.sales_page_sections)
    else:
        packages = (
            db.query(Package)
            .filter(
                Package.id != exclude_id,
                Package.sales_page_sections.isnot(None),
            )
            .limit(limit)
            .all()
        )
        for pkg in packages:
            if pkg.sales_page_sections:
                examples.append(pkg.sales_page_sections)

    # Also check the other entity type if we don't have enough
    if len(examples) < limit:
        remaining = limit - len(examples)
        if entity_type == EntityType.COURSE:
            packages = (
                db.query(Package)
                .filter(Package.sales_page_sections.isnot(None))
                .limit(remaining)
                .all()
            )
            for pkg in packages:
                if pkg.sales_page_sections:
                    examples.append(pkg.sales_page_sections)
        else:
            courses = (
                db.query(Course)
                .filter(Course.sales_page_sections.isnot(None))
                .limit(remaining)
                .all()
            )
            for course in courses:
                if course.sales_page_sections:
                    examples.append(course.sales_page_sections)

    return examples[:limit]


def _extract_json_from_response(text: str) -> dict[str, Any]:
    """Extract JSON from AI response, handling markdown code blocks."""
    # Try extracting from ```json ... ``` code block
    json_match = re.search(r"```json\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if json_match:
        result: dict[str, Any] = json.loads(json_match.group(1))
        return result

    # Try extracting from ``` ... ``` code block
    code_match = re.search(r"```\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_match:
        try:
            code_result: dict[str, Any] = json.loads(code_match.group(1))
            return code_result
        except json.JSONDecodeError:
            pass

    # Try parsing the entire text as JSON
    # Find the first { and last } for the outermost JSON object
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            brace_result: dict[str, Any] = json.loads(text[first_brace : last_brace + 1])
            return brace_result
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from AI response")


def _extract_ai_message(text: str) -> str:
    """Extract the AI's explanation message from the response."""
    # Remove the JSON code block to get the explanation
    cleaned = re.sub(r"```json\s*\n?.*?\n?\s*```", "", text, flags=re.DOTALL).strip()
    if not cleaned:
        cleaned = re.sub(r"```\s*\n?.*?\n?\s*```", "", text, flags=re.DOTALL).strip()
    return cleaned or "Strona sprzedażowa została wygenerowana."


def _validate_and_fix(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and auto-fix the generated sales page data."""
    # Ensure required top-level keys
    if "version" not in data:
        data["version"] = 1
    if "sections" not in data:
        data["sections"] = []
    if "settings" not in data:
        data["settings"] = {"theme": "dark", "custom_css": ""}
    if "theme" not in data["settings"]:
        data["settings"]["theme"] = "dark"
    if "custom_css" not in data["settings"]:
        data["settings"]["custom_css"] = ""

    # Force all AI-generated sections to custom_html — drop predefined types
    original_count = len(data["sections"])
    data["sections"] = [s for s in data["sections"] if s.get("type") == "custom_html"]
    dropped = original_count - len(data["sections"])
    if dropped:
        logger.warning(
            f"Dropped {dropped} non-custom_html sections from AI response "
            f"(kept {len(data['sections'])})"
        )

    # Fix each section
    for i, section in enumerate(data["sections"]):
        # Assign UUID if missing or invalid
        section_id = section.get("id", "")
        try:
            uuid.UUID(section_id)
        except (ValueError, AttributeError):
            section["id"] = str(uuid.uuid4())

        # Fix sort_order to be sequential
        section["sort_order"] = i

        # Ensure visible defaults to True
        if "visible" not in section:
            section["visible"] = True

        # Ensure config exists
        if "config" not in section:
            section["config"] = {}

        # Validate section type and config against SECTION_CONFIG_MAP
        section_type = section.get("type", "")
        if section_type in SECTION_CONFIG_MAP:
            config_cls = SECTION_CONFIG_MAP[section_type]
            try:
                validated = config_cls.model_validate(section["config"])
                section["config"] = validated.model_dump()
            except Exception:
                # Keep original config if validation fails with defaults applied
                pass

    # Validate with Pydantic
    validated_data = SalesPageData.model_validate(data)
    return validated_data.model_dump()


def generate_sales_page(
    db: Session,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    request: AiGenerateRequest,
) -> AiGenerateResponse:
    """Main orchestrator for AI sales page generation."""
    # 1. Fetch product data
    if entity_type == EntityType.COURSE:
        product_data = _fetch_course_data(db, entity_id)
    else:
        product_data = _fetch_bundle_data(db, entity_id)

    # 2. Fetch brand guidelines (optional)
    guidelines: BrandGuidelines | None = get_brand_guidelines(db)

    # 3. Fetch few-shot examples (optional)
    examples: list[dict[str, Any]] = []
    if request.include_few_shot_examples:
        examples = _fetch_few_shot_examples(db, entity_type, entity_id)

    # 4. Build system prompt
    system_prompt = build_system_prompt(
        entity_type=entity_type,
        product_data=product_data,
        guidelines=guidelines,
        examples=examples,
        theme=request.theme,
    )

    # 5. Build messages array
    messages: list[MessageParam] = []

    # Add chat history
    for msg in request.chat_history:
        messages.append(cast(MessageParam, {"role": msg.role, "content": msg.content}))

    # Build current user message
    # For iterative mode (has chat history), prepend current page state
    current_page_data = None
    if request.chat_history:
        # Try to extract current page from the last assistant message
        for msg in reversed(request.chat_history):
            if msg.role == "assistant":
                try:
                    current_page_data = _extract_json_from_response(msg.content)
                except (ValueError, json.JSONDecodeError):
                    pass
                break

    user_message = build_iterative_user_message(request.prompt, current_page_data)
    messages.append(cast(MessageParam, {"role": "user", "content": user_message}))

    # 6. Call Anthropic API
    response_text, tokens_used, model = call_anthropic(
        system_prompt,
        messages,
        max_tokens=settings.ANTHROPIC_MAX_TOKENS_SALES_PAGE,
        temperature=settings.ANTHROPIC_TEMPERATURE,
    )

    # 7. Parse and validate response
    try:
        raw_data = _extract_json_from_response(response_text)
        validated_data = _validate_and_fix(raw_data)
        ai_message = _extract_ai_message(response_text)
    except (ValueError, json.JSONDecodeError) as e:
        # Retry once with error feedback
        logger.warning(f"First AI response parsing failed: {e}. Retrying with feedback.")
        messages.append(cast(MessageParam, {"role": "assistant", "content": response_text}))
        messages.append(
            cast(
                MessageParam,
                {
                    "role": "user",
                    "content": (
                        f"Twoja poprzednia odpowiedź nie zawierała poprawnego JSON. "
                        f"Błąd: {e}. "
                        f"Proszę, odpowiedz ponownie z poprawnym blokiem JSON ```json ... ``` "
                        f"zawierającym kompletny obiekt SalesPageData."
                    ),
                },
            )
        )

        retry_text, retry_tokens, model = call_anthropic(
            system_prompt,
            messages,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS_SALES_PAGE,
            temperature=settings.ANTHROPIC_TEMPERATURE,
        )
        if retry_tokens and tokens_used:
            tokens_used += retry_tokens

        try:
            raw_data = _extract_json_from_response(retry_text)
            validated_data = _validate_and_fix(raw_data)
            ai_message = _extract_ai_message(retry_text)
        except (ValueError, json.JSONDecodeError) as retry_error:
            raise ValueError(
                f"AI nie wygenerowało poprawnego JSON po dwóch próbach. Ostatni błąd: {retry_error}"
            ) from retry_error

    # 8. Return response
    return AiGenerateResponse(
        sales_page_data=validated_data,
        ai_message=ai_message,
        tokens_used=tokens_used,
        model=model,
    )
