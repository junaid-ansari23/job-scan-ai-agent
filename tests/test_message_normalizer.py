import base64
from datetime import UTC, datetime

from app.services.message_normalizer import normalize_gmail_message


def encoded(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def test_normalizes_plain_text_gmail_message() -> None:
    raw = {
        "id": "m1",
        "threadId": "t1",
        "internalDate": "1710000000000",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Recruiter <recruiter@example.com>"},
                {"name": "To", "value": "Candidate <candidate@example.com>"},
                {"name": "Subject", "value": "A role for you"},
            ],
            "body": {"data": encoded("Hello,\n\nWe have a role for you.")},
        },
    }

    message = normalize_gmail_message(raw)

    assert message.message_id == "m1"
    assert message.sender == "Recruiter <recruiter@example.com>"
    assert message.recipients == ["Candidate <candidate@example.com>"]
    assert message.body_text == "Hello, We have a role for you."
    assert message.preview == message.body_text
    assert message.received_at == datetime.fromtimestamp(1710000000, tz=UTC)


def test_prefers_plain_text_from_multipart_message() -> None:
    raw = {
        "id": "m2",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded("Plain role")}},
                {
                    "mimeType": "text/html",
                    "body": {"data": encoded("<p>HTML role</p>")},
                },
            ],
        },
    }

    message = normalize_gmail_message(raw)

    assert message.body_text == "Plain role"


def test_converts_html_when_plain_text_is_unavailable() -> None:
    raw = {
        "id": "m3",
        "payload": {
            "mimeType": "text/html",
            "headers": [],
            "body": {"data": encoded("<h1>Staff Engineer</h1><p>Remote role</p>")},
        },
    }

    assert normalize_gmail_message(raw).body_text == "Staff Engineer Remote role"


def test_handles_missing_and_malformed_fields() -> None:
    message = normalize_gmail_message(
        {"id": "m4", "internalDate": "invalid", "snippet": " fallback  snippet "}
    )

    assert message.received_at is None
    assert message.sender is None
    assert message.body_text == ""
    assert message.preview == "fallback snippet"
