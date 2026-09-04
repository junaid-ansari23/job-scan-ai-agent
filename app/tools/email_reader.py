from typing import Protocol

from app.models.email import EmailMessage


class EmailReader(Protocol):
    """Read-only interface for retrieving normalized email messages."""

    def get_recent_emails(self, hours: int) -> list[EmailMessage]: ...
