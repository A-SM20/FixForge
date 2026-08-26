"""Pydantic schemas for Run request/response validation.

Why separate schemas from ORM models: Decouples API contract from DB schema.
We can evolve the API independently, add computed fields, and exclude
internal columns without touching the ORM.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

# --- Request schemas ---


class RunCreate(BaseModel):
    """Request body for creating a new agent run."""

    issue_url: HttpUrl = Field(..., description="URL of the GitHub issue to fix")
    repo_url: HttpUrl = Field(..., description="URL of the GitHub repository")


# --- Response schemas ---


class PatchSummary(BaseModel):
    """Patch info embedded in RunDetail response."""

    id: uuid.UUID
    iteration_number: int
    test_passed: bool | None
    test_result: str | None
    diff_preview: str = Field(
        ..., description="First 500 chars of the diff for preview"
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class RunListItem(BaseModel):
    """Summary of a run for the dashboard listing."""

    id: uuid.UUID
    issue_url: str
    repo_url: str
    status: str
    state: str
    iteration_count: int
    total_cost: float
    total_latency: float
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class RunDetail(BaseModel):
    """Full run details including patches and metadata."""

    id: uuid.UUID
    issue_url: str
    repo_url: str
    status: str
    state: str
    iteration_count: int
    total_cost: float
    total_latency: float
    pr_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    patches: list[PatchSummary] = []

    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    """Paginated list of runs."""

    items: list[RunListItem]
    total: int
    page: int
    page_size: int
