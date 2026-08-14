"""Run ORM model.

Represents a single agent run: one GitHub issue → one attempted fix.
UUID primary key avoids enumeration attacks and works across distributed
systems. The 'state' column tracks the current FSM state for live UI updates.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Run(Base):
    """A single agent run attempting to fix a GitHub issue."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    repo_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending | running | success | failed | error
    state: Mapped[str] = mapped_column(
        String(30), default="READ_ISSUE", nullable=False
    )  # Current FSM state
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_latency: Mapped[float] = mapped_column(Float, default=0.0)
    pr_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    patches: Mapped[list["Patch"]] = relationship(  # noqa: F821
        "Patch", back_populates="run", cascade="all, delete-orphan",
        order_by="Patch.iteration_number",
    )
    log_entries: Mapped[list["LogEntry"]] = relationship(  # noqa: F821
        "LogEntry", back_populates="run", cascade="all, delete-orphan",
        order_by="LogEntry.created_at",
    )

    def __repr__(self) -> str:
        return f"<Run {self.id} status={self.status} state={self.state}>"
