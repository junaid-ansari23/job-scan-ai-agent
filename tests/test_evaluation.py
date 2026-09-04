from pathlib import Path

import pytest

from app.config import load_preferences
from app.models.domain import (
    Decision,
    EmploymentType,
    JobOpportunity,
    Priority,
    UnknownableBool,
    WorkMode,
)
from app.models.preferences import ScoringThresholds
from app.services.evaluation import evaluate_job


PREFERENCES_PATH = Path("config/preferences.example.yaml")
OPPORTUNITIES_PATH = Path("tests/fixtures/opportunities")


def load_opportunity(name: str) -> JobOpportunity:
    return JobOpportunity.model_validate_json(
        (OPPORTUNITIES_PATH / name).read_text(encoding="utf-8")
    )


def test_strong_match_scores_every_component() -> None:
    result = evaluate_job(load_opportunity("strong_match.json"), load_preferences(PREFERENCES_PATH))

    assert result.fit_score == 100
    assert result.decision == Decision.STRONG_MATCH
    assert result.priority == Priority.HIGH
    assert result.signal_score == 0
    assert [component.name for component in result.fit_components] == [
        "role_match",
        "employment_type",
        "visa",
        "location",
        "work_mode",
        "compensation",
    ]


def test_possible_match_is_explainable() -> None:
    result = evaluate_job(load_opportunity("possible_match.json"), load_preferences(PREFERENCES_PATH))

    assert result.fit_score == 76.25
    assert result.decision == Decision.POSSIBLE_MATCH
    assert result.priority == Priority.NORMAL
    assert "Compensation is unknown." in result.concerns


def test_critical_unknowns_force_needs_review() -> None:
    result = evaluate_job(load_opportunity("needs_review.json"), load_preferences(PREFERENCES_PATH))

    assert result.decision == Decision.NEEDS_REVIEW
    assert result.priority == Priority.NORMAL
    assert result.critical_unknowns == [
        "employment_type",
        "h1b_support",
        "work_mode",
    ]


def test_known_hard_failure_takes_precedence_over_unknown() -> None:
    opportunity = load_opportunity("needs_review.json").model_copy(
        update={"h1b_support": UnknownableBool.NO}
    )

    result = evaluate_job(opportunity, load_preferences(PREFERENCES_PATH))

    assert result.decision == Decision.REJECT
    assert "employment_type" in result.critical_unknowns
    assert any("H1B" in concern for concern in result.concerns)


@pytest.mark.parametrize(
    ("field", "value", "expected_concern"),
    [
        ("employment_type", EmploymentType.PART_TIME, "Employment type"),
        ("work_mode", WorkMode.ONSITE, "Work mode"),
        ("h1b_support", UnknownableBool.NO, "H1B"),
    ],
)
def test_each_known_hard_failure_rejects(
    field: str, value: object, expected_concern: str
) -> None:
    opportunity = load_opportunity("strong_match.json").model_copy(update={field: value})

    result = evaluate_job(opportunity, load_preferences(PREFERENCES_PATH))

    assert result.decision == Decision.REJECT
    assert any(expected_concern in concern for concern in result.concerns)


def test_unknown_role_requires_review() -> None:
    opportunity = load_opportunity("strong_match.json").model_copy(update={"role": None})

    result = evaluate_job(opportunity, load_preferences(PREFERENCES_PATH))

    assert result.decision == Decision.NEEDS_REVIEW
    assert "role" in result.critical_unknowns


def test_generic_engineer_title_does_not_receive_full_role_points() -> None:
    opportunity = load_opportunity("strong_match.json").model_copy(
        update={"role": "Engineer"}
    )

    result = evaluate_job(opportunity, load_preferences(PREFERENCES_PATH))
    role_component = next(
        component for component in result.fit_components if component.name == "role_match"
    )

    assert 0 < role_component.points < 30


def test_nonpreferred_location_lowers_score_but_is_not_hard_failure() -> None:
    opportunity = load_opportunity("strong_match.json").model_copy(
        update={"location": "Seattle, WA"}
    )

    result = evaluate_job(opportunity, load_preferences(PREFERENCES_PATH))

    assert result.fit_score == 85
    assert result.decision == Decision.STRONG_MATCH
    assert "Location is outside configured preferences." in result.concerns


def test_threshold_boundaries_are_inclusive() -> None:
    preferences = load_preferences(PREFERENCES_PATH)
    opportunity = load_opportunity("possible_match.json")
    score = evaluate_job(opportunity, preferences).fit_score

    strong_boundary = preferences.model_copy(deep=True)
    strong_boundary.scoring.thresholds = ScoringThresholds(
        strong_match=score, possible_match=65
    )
    possible_boundary = preferences.model_copy(deep=True)
    possible_boundary.scoring.thresholds = ScoringThresholds(
        strong_match=score + 1, possible_match=score
    )

    assert evaluate_job(opportunity, strong_boundary).decision == Decision.STRONG_MATCH
    assert evaluate_job(opportunity, possible_boundary).decision == Decision.POSSIBLE_MATCH


def test_evaluation_is_deterministic() -> None:
    opportunity = load_opportunity("strong_match.json")
    preferences = load_preferences(PREFERENCES_PATH)

    first = evaluate_job(opportunity, preferences)
    second = evaluate_job(opportunity, preferences)

    assert first == second


def test_non_job_message_is_rejected_without_score_components() -> None:
    opportunity = JobOpportunity(message_id="not-job", job_related=False)

    result = evaluate_job(opportunity, load_preferences(PREFERENCES_PATH))

    assert result.decision == Decision.REJECT
    assert result.fit_score == 0
    assert result.fit_components == []
