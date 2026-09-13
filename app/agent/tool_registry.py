from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from app.agent.models import ToolStatus, ToolTrace
from app.models.domain import EvaluationResult, JobOpportunity
from app.models.email import EmailMessage


class ToolRegistryError(RuntimeError):
    """Base error for bounded tool registration or execution."""


class UnknownToolError(ToolRegistryError):
    pass


class DuplicateToolError(ToolRegistryError):
    pass


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    """One allow-listed callable and its side-effect classification."""

    name: str
    handler: Callable[[Any], Any]
    has_side_effects: bool = False


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    output: Any | None
    trace: ToolTrace


class ToolRegistry:
    """Explicit allow list that executes tools and creates sanitized traces.

    The registry deliberately stores no raw inputs in traces. This prevents an
    email body or future credential-bearing object from being copied into logs.
    """

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def register(self, tool: RegisteredTool) -> None:
        if tool.name in self._tools:
            raise DuplicateToolError(f"Tool is already registered: {tool.name}")
        self._tools[tool.name] = tool

    def invoke(self, name: str, value: Any, *, dry_run: bool) -> ToolInvocation:
        tool = self._tools.get(name)
        if tool is None:
            raise UnknownToolError(f"Tool is not registered: {name}")

        started = monotonic()
        input_summary = _summarize(value)
        if tool.has_side_effects and dry_run:
            return ToolInvocation(
                output=None,
                trace=ToolTrace(
                    tool_name=name,
                    status=ToolStatus.BLOCKED_DRY_RUN,
                    duration_ms=_elapsed_ms(started),
                    input_summary=input_summary,
                    error_type="DryRunBlocked",
                ),
            )

        try:
            output = tool.handler(value)
        except Exception as exc:
            # Exception text is intentionally omitted because third-party errors
            # can echo request content or secrets. The type is enough for routing.
            return ToolInvocation(
                output=None,
                trace=ToolTrace(
                    tool_name=name,
                    status=ToolStatus.FAILED,
                    duration_ms=_elapsed_ms(started),
                    input_summary=input_summary,
                    error_type=type(exc).__name__,
                ),
            )

        return ToolInvocation(
            output=output,
            trace=ToolTrace(
                tool_name=name,
                status=ToolStatus.SUCCEEDED,
                duration_ms=_elapsed_ms(started),
                input_summary=input_summary,
                output_summary=_summarize(output),
            ),
        )


def _elapsed_ms(started: float) -> float:
    return max(0.0, round((monotonic() - started) * 1000, 3))


def _summarize(value: Any) -> dict[str, Any]:
    """Return a small type-aware summary without free-form message content."""

    if isinstance(value, EmailMessage):
        return {
            "type": "EmailMessage",
            "message_id": value.message_id,
            "has_subject": bool(value.subject),
            "body_chars": len(value.body_text),
        }
    if isinstance(value, JobOpportunity):
        return {
            "type": "JobOpportunity",
            "message_id": value.message_id,
            "job_related": value.job_related,
            "source_type": value.source_type.value,
            "confidence": value.confidence,
        }
    if isinstance(value, EvaluationResult):
        return {
            "type": "EvaluationResult",
            "decision": value.decision.value,
            "priority": value.priority.value,
            "fit_score": value.fit_score,
            "critical_unknown_count": len(value.critical_unknowns),
        }
    return {"type": type(value).__name__}
