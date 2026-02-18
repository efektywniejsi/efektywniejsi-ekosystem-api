"""Shared Pydantic schemas for sales_content JSONB field.

Used by both Course and ImplementationPackage to validate
the structured sales content displayed in detail sheets.
"""

from pydantic import BaseModel


class WhatsIncludedItem(BaseModel):
    icon: str = ""
    title: str = ""
    description: str = ""


class OutcomeItem(BaseModel):
    icon: str = ""
    text: str = ""


class FaqItem(BaseModel):
    question: str = ""
    answer: str = ""


class AudienceItem(BaseModel):
    text: str = ""


class SalesContent(BaseModel):
    whats_included: list[WhatsIncludedItem] = []
    outcomes: list[OutcomeItem] = []
    faq: list[FaqItem] = []
    target_audience: list[AudienceItem] = []
    negative_audience: list[AudienceItem] = []
