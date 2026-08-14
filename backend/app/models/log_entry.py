"""LogEntry ORM model.

Structured logging for every LLM call and tool call, tied to a run_id.
Stored in Postgres (not files) so the dashboard can query and aggregate
cost/latency metrics with simple SQL joins.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LogEntry(Base):
    """A structured log entry for an LLM or tool call within a run."""

    __tablename__ = "log_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "llm_call" | "tool_call"
    state: Mapped[str] = mapped_column(String(30), nullable=False)  # FSM state
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tool_args: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_result_preview: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # First 500 chars of tool output
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    run: Mapped["Run"] = relationship("Run", back_populates="log_entries")  # noqa: F821

    def __repr__(self) -> str:
        return f"<LogEntry {self.entry_type} run={self.run_id} state={self.state}>"
