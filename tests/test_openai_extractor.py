from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.domain import (
    EmploymentType,
    JobOpportunity,
    SourceType,
    UnknownableBool,
    WorkMode,
)
from app.models.email import EmailMessage
from app.services.openai_extractor import ExtractionError, OpenAIJobExtractor


def _prompt(tmp_path: Path) -> Path:
    path = tmp_path / "prompt.md"
    path.write_text("Extract supported job facts only.", encoding="utf-8")
    return path


def test_returns_non_job_without_api_call_for_empty_message(tmp_path: Path) -> None:
    client = MagicMock()
    extractor = OpenAIJobExtractor(client, "test-model", _prompt(tmp_path))

    result = extractor.extract(EmailMessage(message_id="empty"))

    assert result.job_related is False
    assert result.confidence == 1.0
    client.responses.parse.assert_not_called()


def test_extracts_structured_result_and_overrides_untrusted_id(tmp_path: Path) -> None:
    parsed = JobOpportunity(
        message_id="model-invented-id",
        job_related=True,
        company="Acme",
        role="Staff AI Engineer",
        employment_type=EmploymentType.FULL_TIME,
        location="San Francisco, CA",
        work_mode=WorkMode.HYBRID,
        h1b_support=UnknownableBool.YES,
        source_type=SourceType.DIRECT_COMPANY_RECRUITER,
        confidence=0.96,
        evidence=["I recruit directly for Acme."],
    )
    client = MagicMock()
    client.responses.parse.return_value = SimpleNamespace(
        output_parsed=parsed,
        usage=SimpleNamespace(input_tokens=100, output_tokens=40),
    )
    extractor = OpenAIJobExtractor(
        client, "test-model", _prompt(tmp_path), max_input_chars=12
    )
    message = EmailMessage(
        message_id="trusted-id",
        sender="Recruiter <r@acme.example>",
        subject="Opportunity",
        body_text="A body longer than twelve characters",
    )

    result = extractor.extract(message)

    assert result.message_id == "trusted-id"
    assert result.company == "Acme"
    call = client.responses.parse.call_args.kwargs
    assert call["model"] == "test-model"
    assert call["text_format"] is JobOpportunity
    assert call["store"] is False
    assert "A body longe" in call["input"][0]["content"]
    assert "than twelve" not in call["input"][0]["content"]


def test_missing_critical_facts_remain_unknown(tmp_path: Path) -> None:
    client = MagicMock()
    client.responses.parse.return_value = SimpleNamespace(
        output_parsed=JobOpportunity(
            message_id="m1",
            job_related=True,
            role="Engineer",
            source_type=SourceType.DIRECT_COMPANY_RECRUITER,
            confidence=0.7,
        ),
        usage=None,
    )

    result = OpenAIJobExtractor(client, "test-model", _prompt(tmp_path)).extract(
        EmailMessage(message_id="m1", subject="Engineering opportunity")
    )

    assert result.h1b_support == UnknownableBool.UNKNOWN
    assert result.employment_type == EmploymentType.UNKNOWN
    assert result.work_mode == WorkMode.UNKNOWN
    assert result.location is None
    assert result.compensation is None


def test_wraps_api_failure_without_returning_partial_result(tmp_path: Path) -> None:
    client = MagicMock()
    client.responses.parse.side_effect = TimeoutError("request timed out")
    extractor = OpenAIJobExtractor(client, "test-model", _prompt(tmp_path))

    with pytest.raises(ExtractionError, match="Extraction failed for message m1"):
        extractor.extract(EmailMessage(message_id="m1", subject="Job opportunity"))


def test_rejects_response_without_parsed_output(tmp_path: Path) -> None:
    client = MagicMock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=None)
    extractor = OpenAIJobExtractor(client, "test-model", _prompt(tmp_path))

    with pytest.raises(ExtractionError, match="no parsed extraction"):
        extractor.extract(EmailMessage(message_id="m1", subject="Job opportunity"))
