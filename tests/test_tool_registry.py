from unittest.mock import MagicMock

import pytest

from app.agent.models import ToolStatus
from app.agent.tool_registry import (
    DuplicateToolError,
    RegisteredTool,
    ToolRegistry,
    UnknownToolError,
)
from app.models.email import EmailMessage


def test_registry_rejects_unknown_tool() -> None:
    with pytest.raises(UnknownToolError, match="not registered"):
        ToolRegistry().invoke("delete_email", object(), dry_run=True)


def test_registry_rejects_duplicate_name() -> None:
    registry = ToolRegistry()
    registry.register(RegisteredTool("extract", lambda value: value))

    with pytest.raises(DuplicateToolError, match="already registered"):
        registry.register(RegisteredTool("extract", lambda value: value))


def test_dry_run_blocks_side_effect_before_handler_runs() -> None:
    handler = MagicMock()
    registry = ToolRegistry()
    registry.register(
        RegisteredTool("label_email", handler, has_side_effects=True)
    )

    invocation = registry.invoke("label_email", {"message_id": "m1"}, dry_run=True)

    assert invocation.output is None
    assert invocation.trace.status == ToolStatus.BLOCKED_DRY_RUN
    handler.assert_not_called()


def test_trace_summarizes_email_without_recording_content() -> None:
    registry = ToolRegistry()
    registry.register(RegisteredTool("inspect", lambda value: value.message_id))
    secret_body = "private email body and secret-token"

    invocation = registry.invoke(
        "inspect",
        EmailMessage(message_id="m1", subject="Private subject", body_text=secret_body),
        dry_run=True,
    )

    serialized = invocation.trace.model_dump_json()
    assert invocation.trace.status == ToolStatus.SUCCEEDED
    assert invocation.trace.input_summary["body_chars"] == len(secret_body)
    assert "private email body" not in serialized
    assert "Private subject" not in serialized
    assert "secret-token" not in serialized


def test_tool_failure_records_type_but_not_exception_message() -> None:
    def fail(_: object) -> None:
        raise RuntimeError("sensitive request contents")

    registry = ToolRegistry()
    registry.register(RegisteredTool("failing_tool", fail))

    invocation = registry.invoke("failing_tool", object(), dry_run=True)

    assert invocation.trace.status == ToolStatus.FAILED
    assert invocation.trace.error_type == "RuntimeError"
    assert "sensitive request contents" not in invocation.trace.model_dump_json()
