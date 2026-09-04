from app.models.domain import (
    EmploymentType,
    JobOpportunity,
    SourceType,
    UnknownableBool,
    WorkMode,
)


def test_job_opportunity_defaults_unknowns():
    opportunity = JobOpportunity(message_id="m1", job_related=True)
    assert opportunity.source_type == SourceType.UNKNOWN
    assert opportunity.h1b_support == UnknownableBool.UNKNOWN
    assert opportunity.employment_type == EmploymentType.UNKNOWN
    assert opportunity.work_mode == WorkMode.UNKNOWN
    assert opportunity.confidence == 0.0


def test_non_job_opportunity_clears_unsupported_job_facts() -> None:
    opportunity = JobOpportunity(
        message_id="m2",
        job_related=False,
        company="Unsupported Company",
        role="Unsupported Role",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.REMOTE,
        h1b_support=UnknownableBool.YES,
        source_type=SourceType.DIRECT_COMPANY_RECRUITER,
    )

    assert opportunity.company is None
    assert opportunity.role is None
    assert opportunity.employment_type == EmploymentType.UNKNOWN
    assert opportunity.work_mode == WorkMode.UNKNOWN
    assert opportunity.h1b_support == UnknownableBool.UNKNOWN
    assert opportunity.source_type == SourceType.UNKNOWN
