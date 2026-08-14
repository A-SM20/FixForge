"""Pydantic schemas for Patch responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class PatchDetail(BaseModel):
    """Full patch detail including complete diff and test output."""

    id: uuid.UUID
    run_id: uuid.UUID
    diff: str
    test_result: str | None = None
    test_passed: bool | None = None
    iteration_number: int
    created_at: datetime

    model_config = {"from_attributes": True}
