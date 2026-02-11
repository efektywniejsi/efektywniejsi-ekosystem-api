from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

ProposalStatusValue = Literal["pending", "approved", "rejected"]


class ProposalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = None
    description: str = Field(..., min_length=10)
    official_docs_url: HttpUrl | None = None


class ProposalUpdate(BaseModel):
    status: ProposalStatusValue
    admin_notes: str | None = None


class ProposalResponse(BaseModel):
    id: UUID
    name: str
    category: str | None
    description: str
    official_docs_url: str | None
    status: str
    admin_notes: str | None
    submitted_by_id: UUID
    submitted_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
