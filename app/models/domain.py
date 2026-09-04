from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class SourceType(str, Enum):
    DIRECT_COMPANY_RECRUITER = "DIRECT_COMPANY_RECRUITER"
    STAFFING_AGENCY = "STAFFING_AGENCY"
    LINKEDIN_DIRECT_MESSAGE = "LINKEDIN_DIRECT_MESSAGE"
    LINKEDIN_JOB_ALERT = "LINKEDIN_JOB_ALERT"
    AUTOMATED_MAILER = "AUTOMATED_MAILER"
    COMPANY_JOB_ALERT = "COMPANY_JOB_ALERT"
    UNKNOWN = "UNKNOWN"


class Decision(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECT = "REJECT"


class Priority(str, Enum):
    URGENT_DIRECT_OUTREACH = "URGENT_DIRECT_OUTREACH"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class UnknownableBool(str, Enum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    CONTRACT = "CONTRACT"
    PART_TIME = "PART_TIME"
    TEMPORARY = "TEMPORARY"
    INTERNSHIP = "INTERNSHIP"
    UNKNOWN = "UNKNOWN"


class WorkMode(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


class JobOpportunity(BaseModel):
    message_id: str
    job_related: bool
    company: Optional[str] = None
    role: Optional[str] = None
    seniority: Optional[str] = None
    employment_type: EmploymentType = EmploymentType.UNKNOWN
    location: Optional[str] = None
    work_mode: WorkMode = WorkMode.UNKNOWN
    compensation: Optional[str] = None
    h1b_support: UnknownableBool = UnknownableBool.UNKNOWN
    recruiter_name: Optional[str] = None
    sender_organization: Optional[str] = None
    job_url: Optional[str] = None
    source_type: SourceType = SourceType.UNKNOWN
    personalized_outreach: UnknownableBool = UnknownableBool.UNKNOWN
    profile_reference: UnknownableBool = UnknownableBool.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def clear_unsupported_non_job_facts(self) -> "JobOpportunity":
        """A non-job classification cannot carry opportunity-specific claims."""

        if self.job_related:
            return self
        self.company = None
        self.role = None
        self.seniority = None
        self.employment_type = EmploymentType.UNKNOWN
        self.location = None
        self.work_mode = WorkMode.UNKNOWN
        self.compensation = None
        self.h1b_support = UnknownableBool.UNKNOWN
        self.recruiter_name = None
        self.sender_organization = None
        self.job_url = None
        self.source_type = SourceType.UNKNOWN
        self.personalized_outreach = UnknownableBool.UNKNOWN
        self.profile_reference = UnknownableBool.UNKNOWN
        return self


class ScoreComponent(BaseModel):
    name: str
    points: float
    reason: str


class EvaluationResult(BaseModel):
    fit_score: float = Field(ge=0, le=100)
    signal_score: float = Field(ge=0, le=100)
    decision: Decision
    priority: Priority
    reasons: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    critical_unknowns: list[str] = Field(default_factory=list)
    fit_components: list[ScoreComponent] = Field(default_factory=list)
    signal_components: list[ScoreComponent] = Field(default_factory=list)
