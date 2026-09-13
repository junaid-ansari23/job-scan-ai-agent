from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.domain import EvaluationResult, JobOpportunity


class RunStatus(str, Enum):
    """Terminal and non-terminal outcomes for one message-processing run."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ITERATION_LIMIT = "ITERATION_LIMIT"


class AgentStage(str, Enum):
    """State-machine stages used to choose the next bounded tool."""

    NEEDS_EXTRACTION = "NEEDS_EXTRACTION"
    NEEDS_EVALUATION = "NEEDS_EVALUATION"
    FINISHED = "FINISHED"


class ToolStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED_DRY_RUN = "BLOCKED_DRY_RUN"


class ToolTrace(BaseModel):
    """Sanitized observability record; raw tool arguments are never persisted."""

    tool_name: str
    status: ToolStatus
    started_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    duration_ms: float = Field(ge=0)
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    error_type: str | None = None


class AgentState(BaseModel):
    """Complete in-memory state for processing exactly one email message."""

    run_id: str
    message_id: str
    status: RunStatus = RunStatus.RUNNING
    stage: AgentStage = AgentStage.NEEDS_EXTRACTION
    iteration_count: int = Field(default=0, ge=0)
    max_iterations: int = Field(ge=1)
    dry_run: bool = True
    opportunity: JobOpportunity | None = None
    evaluation: EvaluationResult | None = None
    traces: list[ToolTrace] = Field(default_factory=list)
    error_code: str | None = None
    error_summary: str | None = None
