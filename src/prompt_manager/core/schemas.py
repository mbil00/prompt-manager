"""Pydantic schemas for API validation and serialization."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PromptBase(BaseModel):
    """Base schema with common prompt fields."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    tags: list[str] = Field(default_factory=list)
    source_url: str | None = Field(None, max_length=2000)
    is_template: bool = False
    template_vars: dict[str, Any] = Field(default_factory=dict)
    success_notes: str | None = None
    failure_notes: str | None = None
    related_slugs: list[str] = Field(default_factory=list)


class PromptCreate(PromptBase):
    """Schema for creating a new prompt."""

    slug: str | None = Field(None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")


class PromptUpdate(BaseModel):
    """Schema for updating an existing prompt."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    source_url: str | None = Field(None, max_length=2000)
    is_template: bool | None = None
    template_vars: dict[str, Any] | None = None
    success_notes: str | None = None
    failure_notes: str | None = None
    related_slugs: list[str] | None = None
    change_note: str | None = Field(None, max_length=500, description="Note for version history")


class PromptRead(PromptBase):
    """Schema for reading a prompt."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    usage_count: int
    last_used_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class PromptVersionRead(BaseModel):
    """Schema for reading a prompt version."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    prompt_id: str
    version: int
    content: str
    changed_at: datetime
    change_note: str | None


class PromptList(BaseModel):
    """Schema for paginated prompt list."""

    items: list[PromptRead]
    total: int
    page: int
    page_size: int
    pages: int


class CategoryCount(BaseModel):
    """Schema for category with count."""

    category: str
    count: int


class TagCount(BaseModel):
    """Schema for tag with count."""

    tag: str
    count: int


class Stats(BaseModel):
    """Schema for usage statistics."""

    total_prompts: int
    total_categories: int
    total_tags: int
    total_usage: int
    most_used: list[PromptRead]
    recently_used: list[PromptRead]
    recently_added: list[PromptRead]


class RenderRequest(BaseModel):
    """Schema for template rendering request."""

    variables: dict[str, Any] = Field(default_factory=dict)


class RenderResponse(BaseModel):
    """Schema for template rendering response."""

    content: str
    slug: str
    is_template: bool
    variables_used: dict[str, Any]
