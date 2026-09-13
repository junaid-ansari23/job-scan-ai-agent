from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.main import _load_email_fixture, _load_opportunity, main
from app.models.domain import JobOpportunity
from app.models.email import EmailMessage


def test_scan_prints_safe_preview_without_full_body(
    capsys: object, tmp_path: Path
) -> None:
    preferences_file = tmp_path / "preferences.yaml"
    preferences_file.write_text(
        Path("config/preferences.example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    reader = MagicMock()
    reader.get_recent_emails.return_value = [
        EmailMessage(
            message_id="m1",
            subject="Opportunity",
            body_text="private full body",
            preview="short preview",
        )
    ]

    with (
        patch("app.main.create_gmail_service", return_value=MagicMock()),
        patch("app.main.GmailEmailReader", return_value=reader),
    ):
        result = main(
            ["scan", "--hours", "12", "--dry-run", "--preferences", str(preferences_file)]
        )

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert result == 0
    assert '"message_id": "m1"' in output
    assert "short preview" in output
    assert "private full body" not in output
    reader.get_recent_emails.assert_called_once_with(12)


def test_load_email_fixture_validates_json(tmp_path: Path) -> None:
    fixture = tmp_path / "email.json"
    fixture.write_text(
        '{"message_id":"fixture-1","subject":"Job opportunity"}',
        encoding="utf-8",
    )

    message = _load_email_fixture(fixture)

    assert message.message_id == "fixture-1"


def test_load_email_fixture_rejects_invalid_json(tmp_path: Path) -> None:
    fixture = tmp_path / "invalid.json"
    fixture.write_text("not-json", encoding="utf-8")

    try:
        _load_email_fixture(fixture)
    except ValueError as exc:
        assert "Invalid email fixture" in str(exc)
    else:
        raise AssertionError("Expected invalid fixture to raise ValueError")


def test_evaluate_command_requires_no_external_service(capsys: object) -> None:
    result = main(
        [
            "evaluate",
            "--opportunity",
            "tests/fixtures/opportunities/strong_match.json",
            "--preferences",
            "config/preferences.example.yaml",
        ]
    )

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert result == 0
    assert '"fit_score": 100.0' in output
    assert '"decision": "STRONG_MATCH"' in output


def test_load_opportunity_rejects_invalid_json(tmp_path: Path) -> None:
    fixture = tmp_path / "invalid-opportunity.json"
    fixture.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid job opportunity"):
        _load_opportunity(fixture)


def test_process_command_prints_completed_state_without_email_body(
    monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    extractor = MagicMock()
    extractor.extract.return_value = JobOpportunity.model_validate_json(
        Path("tests/fixtures/opportunities/strong_match.json").read_text(
            encoding="utf-8"
        )
    ).model_copy(update={"message_id": "fixture-direct-recruiter"})

    with (
        patch("openai.OpenAI", return_value=MagicMock()),
        patch("app.main.OpenAIJobExtractor", return_value=extractor),
    ):
        result = main(
            [
                "process",
                "--file",
                "tests/fixtures/direct_recruiter.json",
                "--preferences",
                "config/preferences.example.yaml",
            ]
        )

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert result == 0
    assert '"status": "COMPLETED"' in output
    assert '"decision": "STRONG_MATCH"' in output
    assert "I found your profile" not in output
