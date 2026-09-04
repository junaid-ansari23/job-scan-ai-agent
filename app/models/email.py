from datetime import datetime

from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    """Provider-independent representation of an email message."""

    message_id: str
    thread_id: str | None = None
    sender: str | None = None
    recipients: list[str] = Field(default_factory=list)
    subject: str | None = None
    received_at: datetime | None = None
    body_text: str = ""
    preview: str = ""
    labels: list[str] = Field(default_factory=list)
