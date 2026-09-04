import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.models.email import EmailMessage
from app.services.message_normalizer import normalize_gmail_message

LOGGER = logging.getLogger(__name__)
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def create_gmail_service(credentials_file: Path, token_file: Path) -> Any:
    """Create an authenticated Gmail service with read-only permissions."""

    credentials: Credentials | None = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(
            str(token_file), [GMAIL_READONLY_SCOPE]
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not credentials_file.is_file():
            raise FileNotFoundError(
                f"Gmail OAuth credentials not found: {credentials_file}. "
                "Download an OAuth desktop-client credentials file from Google Cloud."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_file), [GMAIL_READONLY_SCOPE]
        )
        credentials = flow.run_local_server(port=0)

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


class GmailEmailReader:
    def __init__(self, service: Any) -> None:
        self._service = service

    def get_recent_emails(self, hours: int) -> list[EmailMessage]:
        if hours < 1:
            raise ValueError("hours must be at least 1")

        cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)
        query = f"after:{int(cutoff.timestamp())}"
        message_refs: list[dict[str, str]] = []
        page_token: str | None = None

        while True:
            request = self._service.users().messages().list(
                userId="me", q=query, pageToken=page_token
            )
            response = request.execute()
            message_refs.extend(response.get("messages", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        LOGGER.info("gmail_messages_discovered", extra={"count": len(message_refs)})
        messages: list[EmailMessage] = []
        for reference in message_refs:
            raw = (
                self._service.users()
                .messages()
                .get(userId="me", id=reference["id"], format="full")
                .execute()
            )
            messages.append(normalize_gmail_message(raw))
        return messages
