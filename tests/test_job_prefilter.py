from app.models.email import EmailMessage
from app.services.job_prefilter import PrefilterResult, prefilter_message


def test_prefilter_identifies_empty_message() -> None:
    assert (
        prefilter_message(EmailMessage(message_id="empty")) == PrefilterResult.EMPTY
    )


def test_prefilter_identifies_job_language() -> None:
    message = EmailMessage(message_id="job", subject="New engineering opportunity")

    assert prefilter_message(message) == PrefilterResult.POSSIBLE_JOB


def test_prefilter_preserves_ambiguous_message_for_model_review() -> None:
    message = EmailMessage(message_id="ambiguous", subject="Could we speak?")

    assert prefilter_message(message) == PrefilterResult.UNKNOWN
