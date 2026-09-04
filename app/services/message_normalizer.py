import base64
import re
from datetime import UTC, datetime
from email.header import decode_header, make_header
from html.parser import HTMLParser
from typing import Any

from app.models.email import EmailMessage


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(self.parts)


def _decode_header(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(make_header(decode_header(value))).strip() or None
    except (LookupError, UnicodeDecodeError):
        return value.strip() or None


def _decode_body(data: str | None) -> str:
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return ""


def _html_to_text(value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(value)
    return parser.text()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_body(payload: dict[str, Any]) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []

    def visit(part: dict[str, Any]) -> None:
        mime_type = part.get("mimeType", "")
        body = _decode_body(part.get("body", {}).get("data"))
        if mime_type == "text/plain" and body:
            plain_parts.append(body)
        elif mime_type == "text/html" and body:
            html_parts.append(_html_to_text(body))
        for child in part.get("parts", []):
            visit(child)

    visit(payload)
    selected = plain_parts if plain_parts else html_parts
    return _clean_text("\n".join(selected))


def normalize_gmail_message(raw: dict[str, Any], preview_length: int = 240) -> EmailMessage:
    """Convert a Gmail API message resource into the application email model."""

    payload = raw.get("payload") or {}
    headers = {
        str(header.get("name", "")).lower(): str(header.get("value", ""))
        for header in payload.get("headers", [])
    }
    recipients = [
        decoded
        for key in ("to", "cc")
        if (decoded := _decode_header(headers.get(key))) is not None
    ]
    body_text = _extract_body(payload)
    received_at = None
    internal_date = raw.get("internalDate")
    if internal_date:
        try:
            received_at = datetime.fromtimestamp(int(internal_date) / 1000, tz=UTC)
        except (TypeError, ValueError, OSError):
            received_at = None

    snippet = _clean_text(str(raw.get("snippet", "")))
    preview_source = body_text or snippet
    preview = preview_source[:preview_length]

    return EmailMessage(
        message_id=str(raw.get("id", "")),
        thread_id=raw.get("threadId"),
        sender=_decode_header(headers.get("from")),
        recipients=recipients,
        subject=_decode_header(headers.get("subject")),
        received_at=received_at,
        body_text=body_text,
        preview=preview,
        labels=[str(label) for label in raw.get("labelIds", [])],
    )
