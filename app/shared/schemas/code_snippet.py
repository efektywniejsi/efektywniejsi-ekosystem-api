"""Shared Pydantic schema for code snippets stored as JSONB.

Used by both Process and Lesson to validate the structured
code snippet data for syntax-highlighted display.
"""

from typing import Literal

from pydantic import BaseModel, Field

AllowedLanguage = Literal[
    "javascript",
    "typescript",
    "python",
    "bash",
    "json",
    "sql",
    "yaml",
    "html",
    "css",
    "docker",
    "markdown",
    "jsx",
    "tsx",
    "text",
]


class CodeSnippet(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    language: AllowedLanguage
    code: str = Field(..., min_length=1, max_length=50_000)
