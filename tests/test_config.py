from pathlib import Path

import pytest

from app.config import Settings, load_preferences
from app.models.preferences import EmploymentPreferences, ScoringThresholds, ScoringWeights


def test_load_example_preferences() -> None:
    preferences = load_preferences(Path("config/preferences.example.yaml"))

    assert preferences.visa.h1b_support_required is True
    assert preferences.gmail.lookback_hours == 24
    assert preferences.gmail.labels.processed == "Jobs/Processed"


def test_load_preferences_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Copy config/preferences.example.yaml"):
        load_preferences(tmp_path / "missing.yaml")


def test_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GMAIL_CREDENTIALS_FILE", raising=False)
    settings = Settings(_env_file=None)

    assert settings.gmail_credentials_file == Path("credentials.json")
    assert settings.gmail_token_file == Path("token.json")
    assert settings.dry_run is True


def test_rejects_reversed_scoring_thresholds() -> None:
    with pytest.raises(ValueError, match="strong_match"):
        ScoringThresholds(strong_match=60, possible_match=80)


def test_rejects_preferred_employment_outside_allowed_values() -> None:
    with pytest.raises(ValueError, match="must be included"):
        EmploymentPreferences(allowed=["contract"], preferred="full_time")


def test_rejects_all_zero_scoring_weights() -> None:
    with pytest.raises(ValueError, match="at least one"):
        ScoringWeights(
            role_match=0,
            employment_type=0,
            visa=0,
            location=0,
            work_mode=0,
            compensation=0,
        )
