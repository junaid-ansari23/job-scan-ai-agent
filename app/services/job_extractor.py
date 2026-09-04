from typing import Protocol

from app.models.domain import JobOpportunity
from app.models.email import EmailMessage


class JobExtractor(Protocol):
    """Provider-independent structured job extraction boundary."""

    def extract(self, message: EmailMessage) -> JobOpportunity: ...
