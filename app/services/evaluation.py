import re

from app.models.domain import (
    Decision,
    EmploymentType,
    EvaluationResult,
    JobOpportunity,
    Priority,
    ScoreComponent,
    UnknownableBool,
    WorkMode,
)
from app.models.preferences import Preferences


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _role_similarity(role: str, target: str) -> float:
    role_normalized = _normalize(role)
    target_normalized = _normalize(target)
    seniority_tokens = {"junior", "senior", "staff", "principal", "lead"}
    role_tokens = set(role_normalized.split("_")) - seniority_tokens
    target_tokens = set(target_normalized.split("_")) - seniority_tokens
    if not role_tokens or not target_tokens:
        return 0.0
    if role_tokens == target_tokens:
        return 1.0
    return len(role_tokens & target_tokens) / len(target_tokens)


def _location_matches(location: str, preferred: str) -> bool:
    actual = _normalize(location)
    wanted = _normalize(preferred)
    return actual == wanted or actual in wanted or wanted in actual


def evaluate_job(
    opportunity: JobOpportunity, preferences: Preferences
) -> EvaluationResult:
    """Evaluate an extracted opportunity using deterministic business rules."""

    weights = preferences.scoring.weights
    components: list[ScoreComponent] = []
    reasons: list[str] = []
    concerns: list[str] = []
    critical_unknowns: list[str] = []
    hard_failures: list[str] = []

    if not opportunity.job_related:
        return EvaluationResult(
            fit_score=0,
            signal_score=0,
            decision=Decision.REJECT,
            priority=Priority.LOW,
            reasons=["Message is not job-related."],
            concerns=[],
            critical_unknowns=[],
            fit_components=[],
            signal_components=[],
        )

    if opportunity.role:
        best_target = max(
            preferences.profile.target_roles,
            key=lambda target: _role_similarity(opportunity.role or "", target),
        )
        similarity = _role_similarity(opportunity.role, best_target)
        points = weights.role_match * similarity
        components.append(
            ScoreComponent(
                name="role_match",
                points=points,
                reason=f"Role best matches '{best_target}' at {similarity:.0%}.",
            )
        )
        if similarity == 1:
            reasons.append(f"Role matches target role '{best_target}'.")
        elif similarity > 0:
            concerns.append(f"Role only partially matches target role '{best_target}'.")
        else:
            concerns.append("Role does not match a configured target role.")
    else:
        critical_unknowns.append("role")
        components.append(ScoreComponent(name="role_match", points=0, reason="Role is unknown."))

    allowed_employment = {_normalize(value) for value in preferences.employment.allowed}
    preferred_employment = _normalize(preferences.employment.preferred)
    employment = _normalize(opportunity.employment_type.value)
    if opportunity.employment_type == EmploymentType.UNKNOWN:
        critical_unknowns.append("employment_type")
        employment_points = 0.0
        employment_reason = "Employment type is unknown."
    elif employment not in allowed_employment:
        hard_failures.append(
            f"Employment type {opportunity.employment_type.value} is not allowed."
        )
        employment_points = 0.0
        employment_reason = "Employment type fails a hard requirement."
    elif employment == preferred_employment:
        employment_points = weights.employment_type
        employment_reason = "Employment type is preferred."
        reasons.append("Employment type is preferred.")
    else:
        employment_points = weights.employment_type * 0.75
        employment_reason = "Employment type is allowed but not preferred."
        reasons.append("Employment type is allowed.")
    components.append(
        ScoreComponent(
            name="employment_type",
            points=employment_points,
            reason=employment_reason,
        )
    )

    if preferences.visa.h1b_support_required:
        if opportunity.h1b_support == UnknownableBool.NO:
            hard_failures.append("Required H1B support is explicitly unavailable.")
            visa_points = 0.0
            visa_reason = "H1B support fails a hard requirement."
        elif opportunity.h1b_support == UnknownableBool.UNKNOWN:
            critical_unknowns.append("h1b_support")
            visa_points = 0.0
            visa_reason = "Required H1B support is unknown."
        else:
            visa_points = weights.visa
            visa_reason = "Required H1B support is available."
            reasons.append("Required H1B support is available.")
    else:
        visa_points = weights.visa
        visa_reason = "H1B support is not a hard requirement."
    components.append(ScoreComponent(name="visa", points=visa_points, reason=visa_reason))

    if not preferences.location.preferred:
        location_points = weights.location
        location_reason = "No preferred locations are configured."
    elif opportunity.location is None:
        location_points = 0.0
        location_reason = "Location is unknown."
        concerns.append("Location is unknown.")
    elif any(
        _location_matches(opportunity.location, preferred)
        for preferred in preferences.location.preferred
    ):
        location_points = weights.location
        location_reason = "Location matches a configured preference."
        reasons.append("Location matches a configured preference.")
    else:
        location_points = 0.0
        location_reason = "Location does not match a configured preference."
        concerns.append("Location is outside configured preferences.")
    components.append(
        ScoreComponent(name="location", points=location_points, reason=location_reason)
    )

    acceptable_modes = {
        _normalize(value) for value in preferences.location.acceptable_work_modes
    }
    work_mode = _normalize(opportunity.work_mode.value)
    if opportunity.work_mode == WorkMode.UNKNOWN:
        critical_unknowns.append("work_mode")
        work_mode_points = 0.0
        work_mode_reason = "Work mode is unknown."
    elif acceptable_modes and work_mode not in acceptable_modes:
        hard_failures.append(f"Work mode {opportunity.work_mode.value} is not acceptable.")
        work_mode_points = 0.0
        work_mode_reason = "Work mode fails a hard requirement."
    else:
        work_mode_points = weights.work_mode
        work_mode_reason = "Work mode is acceptable."
        reasons.append("Work mode is acceptable.")
    components.append(
        ScoreComponent(name="work_mode", points=work_mode_points, reason=work_mode_reason)
    )

    if opportunity.compensation:
        compensation_points = weights.compensation
        compensation_reason = "Compensation information is available."
        reasons.append("Compensation information is available.")
    else:
        compensation_points = 0.0
        compensation_reason = "Compensation is unknown."
        concerns.append("Compensation is unknown.")
    components.append(
        ScoreComponent(
            name="compensation", points=compensation_points, reason=compensation_reason
        )
    )

    raw_score = sum(component.points for component in components)
    total_weight = sum(weights.model_dump().values())
    fit_score = round(min(100.0, max(0.0, raw_score / total_weight * 100)), 2)

    if hard_failures:
        decision = Decision.REJECT
        priority = Priority.LOW
        concerns = hard_failures + concerns
    elif critical_unknowns:
        decision = Decision.NEEDS_REVIEW
        priority = Priority.NORMAL
    elif fit_score >= preferences.scoring.thresholds.strong_match:
        decision = Decision.STRONG_MATCH
        priority = Priority.HIGH
    elif fit_score >= preferences.scoring.thresholds.possible_match:
        decision = Decision.POSSIBLE_MATCH
        priority = Priority.NORMAL
    else:
        decision = Decision.REJECT
        priority = Priority.LOW
        concerns.append("Fit score is below the possible-match threshold.")

    return EvaluationResult(
        fit_score=fit_score,
        signal_score=0,
        decision=decision,
        priority=priority,
        reasons=reasons,
        concerns=concerns,
        critical_unknowns=critical_unknowns,
        fit_components=components,
        signal_components=[],
    )
