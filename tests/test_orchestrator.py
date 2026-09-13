from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

from app.agent.models import AgentStage, RunStatus, ToolStatus
from app.agent.orchestrator import JobTriageOrchestrator
from app.agent.tool_registry import RegisteredTool, ToolRegistry
from app.config import load_preferences
from app.models.domain import Decision, JobOpportunity
from app.models.email import EmailMessage
from app.services.job_extractor import JobExtractor


PREFERENCES = load_preferences(Path("config/preferences.example.yaml"))


def _message(body: str = "Private recruiter email") -> EmailMessage:
    return EmailMessage(
        message_id="m1",
        subject="Staff AI Engineer opportunity",
        body_text=body,
    )


def _opportunity(*, job_related: bool = True) -> JobOpportunity:
    return JobOpportunity.model_validate_json(
        Path("tests/fixtures/opportunities/strong_match.json").read_text(
            encoding="utf-8"
        )
    ).model_copy(update={"message_id": "m1", "job_related": job_related})


def test_orchestrator_completes_extract_then_evaluate() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = _opportunity()

    state = JobTriageOrchestrator(
        cast(JobExtractor, extractor), PREFERENCES
    ).process(_message())

    assert state.status == RunStatus.COMPLETED
    assert state.stage == AgentStage.FINISHED
    assert state.iteration_count == 2
    assert state.evaluation is not None
    assert state.evaluation.decision == Decision.STRONG_MATCH
    assert [trace.tool_name for trace in state.traces] == [
        "extract_job_information",
        "evaluate_job",
    ]
    assert all(trace.status == ToolStatus.SUCCEEDED for trace in state.traces)


def test_non_job_extraction_still_receives_deterministic_evaluation() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = JobOpportunity(message_id="m1", job_related=False)

    state = JobTriageOrchestrator(
        cast(JobExtractor, extractor), PREFERENCES
    ).process(_message())

    assert state.status == RunStatus.COMPLETED
    assert state.evaluation is not None
    assert state.evaluation.decision == Decision.REJECT
    assert state.evaluation.reasons == ["Message is not job-related."]


def test_extraction_failure_terminates_with_structured_error() -> None:
    extractor = MagicMock()
    extractor.extract.side_effect = TimeoutError("email body must not appear")

    state = JobTriageOrchestrator(
        cast(JobExtractor, extractor), PREFERENCES
    ).process(_message("email body must not appear"))

    assert state.status == RunStatus.FAILED
    assert state.error_code == "TimeoutError"
    assert state.opportunity is None
    assert state.evaluation is None
    assert state.iteration_count == 1
    assert "email body must not appear" not in state.model_dump_json()


def test_iteration_limit_stops_before_unbounded_second_tool() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = _opportunity()

    state = JobTriageOrchestrator(
        cast(JobExtractor, extractor), PREFERENCES, max_iterations=1
    ).process(_message())

    assert state.status == RunStatus.ITERATION_LIMIT
    assert state.stage == AgentStage.NEEDS_EVALUATION
    assert state.opportunity is not None
    assert state.evaluation is None
    assert state.iteration_count == 1
    assert state.error_code == "MAX_ITERATIONS_EXCEEDED"


def test_unexpected_tool_output_fails_closed() -> None:
    registry = ToolRegistry()
    registry.register(
        RegisteredTool("extract_job_information", lambda _: "invalid output")
    )
    registry.register(RegisteredTool("evaluate_job", lambda _: "invalid output"))
    extractor = MagicMock()

    state = JobTriageOrchestrator(
        cast(JobExtractor, extractor), PREFERENCES, registry=registry
    ).process(_message())

    assert state.status == RunStatus.FAILED
    assert state.error_code == "INVALID_TOOL_OUTPUT"
    assert state.opportunity is None


def test_each_run_gets_a_distinct_traceable_run_id() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = _opportunity()
    orchestrator = JobTriageOrchestrator(cast(JobExtractor, extractor), PREFERENCES)

    first = orchestrator.process(_message())
    second = orchestrator.process(_message())

    assert first.run_id != second.run_id


def test_mismatched_extraction_message_id_fails_closed() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = _opportunity().model_copy(
        update={"message_id": "different-message"}
    )

    state = JobTriageOrchestrator(
        cast(JobExtractor, extractor), PREFERENCES
    ).process(_message())

    assert state.status == RunStatus.FAILED
    assert state.error_code == "MESSAGE_ID_MISMATCH"
    assert state.opportunity is None
