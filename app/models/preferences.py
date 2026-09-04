from pydantic import BaseModel, Field, model_validator


class ProfilePreferences(BaseModel):
    target_roles: list[str] = Field(min_length=1)


class EmploymentPreferences(BaseModel):
    allowed: list[str] = Field(min_length=1)
    preferred: str

    @model_validator(mode="after")
    def preferred_must_be_allowed(self) -> "EmploymentPreferences":
        allowed = {_normalize(value) for value in self.allowed}
        if _normalize(self.preferred) not in allowed:
            raise ValueError("employment.preferred must be included in employment.allowed")
        return self


class VisaPreferences(BaseModel):
    h1b_support_required: bool = False
    accepted_values: list[str] = Field(default_factory=list)


class LocationPreferences(BaseModel):
    preferred: list[str] = Field(default_factory=list)
    acceptable_work_modes: list[str] = Field(default_factory=list)


class ScoringThresholds(BaseModel):
    strong_match: float = Field(ge=0, le=100)
    possible_match: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def thresholds_must_be_ordered(self) -> "ScoringThresholds":
        if self.strong_match < self.possible_match:
            raise ValueError("strong_match must be greater than or equal to possible_match")
        return self


class ScoringWeights(BaseModel):
    role_match: float = Field(ge=0)
    employment_type: float = Field(ge=0)
    visa: float = Field(ge=0)
    location: float = Field(ge=0)
    work_mode: float = Field(ge=0)
    compensation: float = Field(ge=0)

    @model_validator(mode="after")
    def at_least_one_weight_is_positive(self) -> "ScoringWeights":
        if sum(self.model_dump().values()) <= 0:
            raise ValueError("at least one scoring weight must be positive")
        return self


class ScoringPreferences(BaseModel):
    thresholds: ScoringThresholds
    weights: ScoringWeights


class SourceSignalPreferences(BaseModel):
    weights: dict[str, float]


class UnsubscribePolicy(BaseModel):
    enabled: bool = True
    minimum_job_messages: int = Field(default=8, ge=1)
    max_positive_match_rate: float = Field(default=0.10, ge=0, le=1)
    minimum_reject_rate: float = Field(default=0.70, ge=0, le=1)
    require_zero_strong_matches: bool = True


class GmailLabels(BaseModel):
    direct_outreach: str
    strong_match: str
    possible_match: str
    needs_review: str
    rejected: str
    processed: str


class GmailPreferences(BaseModel):
    lookback_hours: int = Field(default=24, ge=1, le=24 * 30)
    labels: GmailLabels


class Preferences(BaseModel):
    profile: ProfilePreferences
    employment: EmploymentPreferences
    visa: VisaPreferences
    location: LocationPreferences
    scoring: ScoringPreferences
    source_signal: SourceSignalPreferences
    unsubscribe_policy: UnsubscribePolicy
    gmail: GmailPreferences


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")
