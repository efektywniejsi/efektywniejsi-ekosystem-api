from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class EntityType(StrEnum):
    COURSE = "course"
    BUNDLE = "bundle"


class AiChatMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str


class AiGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    chat_history: list[AiChatMessage] = Field(default_factory=list)
    include_few_shot_examples: bool = True
    theme: Literal["dark", "light"] = "dark"


class AiGenerateResponse(BaseModel):
    sales_page_data: dict
    ai_message: str
    tokens_used: int | None = None
    model: str


class AiTaskCreatedResponse(BaseModel):
    task_id: str


class AiTaskStatusResponse(BaseModel):
    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    result: AiGenerateResponse | None = None
    error: str | None = None


class AiChatSessionMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ai_message: str | None = None
    sales_page_data: dict | None = None
    tokens_used: int | None = None
    model: str | None = None


class AiChatSessionResponse(BaseModel):
    entity_type: EntityType
    entity_id: str
    messages: list[AiChatSessionMessage] = Field(default_factory=list)
    pending_task_id: str | None = None
    pending_response: AiGenerateResponse | None = None
