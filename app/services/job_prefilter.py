from enum import Enum

from app.models.email import EmailMessage


class PrefilterResult(str, Enum):
    EMPTY = "EMPTY"
    POSSIBLE_JOB = "POSSIBLE_JOB"
    UNKNOWN = "UNKNOWN"


JOB_TERMS = (
    "career",
    "hiring",
    "interview",
    "job",
    "opportunity",
    "position",
    "recruiter",
    "role",
)


def prefilter_message(message: EmailMessage) -> PrefilterResult:
    """Identify empty input and likely job mail without rejecting ambiguity."""

    content = f"{message.subject or ''}\n{message.body_text}".strip().lower()
    if not content:
        return PrefilterResult.EMPTY
    if any(term in content for term in JOB_TERMS):
        return PrefilterResult.POSSIBLE_JOB
    return PrefilterResult.UNKNOWN
