import json
import logging
from pathlib import Path
from time import monotonic
from typing import Any

from app.models.domain import JobOpportunity
from app.models.email import EmailMessage
from app.services.job_prefilter import PrefilterResult, prefilter_message

LOGGER = logging.getLogger(__name__)


class ExtractionError(RuntimeError):
    """Raised when structured extraction cannot produce a validated result."""


class OpenAIJobExtractor:
    def __init__(
        self,
        client: Any,
        model: str,
        prompt_path: Path = Path("prompts/job_extraction.md"),
        max_input_chars: int = 20_000,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not model.strip():
            raise ValueError("An OpenAI model is required for extraction.")
        if max_input_chars < 1:
            raise ValueError("max_input_chars must be at least 1")
        self._client = client
        self._model = model
        self._prompt_path = prompt_path
        self._max_input_chars = max_input_chars
        self._timeout_seconds = timeout_seconds

    def extract(self, message: EmailMessage) -> JobOpportunity:
        prefilter = prefilter_message(message)
        if prefilter == PrefilterResult.EMPTY:
            return JobOpportunity(
                message_id=message.message_id,
                job_related=False,
                confidence=1.0,
                evidence=["Message contains no subject or body text."],
            )

        if not self._prompt_path.is_file():
            raise ExtractionError(f"Extraction prompt not found: {self._prompt_path}")

        prompt = self._prompt_path.read_text(encoding="utf-8")
        input_payload = json.dumps(
            {
                "message_id": message.message_id,
                "sender": message.sender,
                "subject": message.subject,
                "body_text": message.body_text[: self._max_input_chars],
            },
            ensure_ascii=False,
        )
        started = monotonic()
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=prompt,
                input=[{"role": "user", "content": input_payload}],
                text_format=JobOpportunity,
                store=False,
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            LOGGER.exception(
                "job_extraction_failed",
                extra={"message_id": message.message_id, "model": self._model},
            )
            raise ExtractionError(
                f"Extraction failed for message {message.message_id}: {exc}"
            ) from exc

        opportunity = getattr(response, "output_parsed", None)
        if opportunity is None:
            raise ExtractionError(
                f"Model returned no parsed extraction for message {message.message_id}."
            )
        if not isinstance(opportunity, JobOpportunity):
            try:
                opportunity = JobOpportunity.model_validate(opportunity)
            except Exception as exc:
                raise ExtractionError(
                    f"Model returned invalid extraction for message {message.message_id}."
                ) from exc

        # The provider cannot choose the identity of the local source message.
        opportunity.message_id = message.message_id
        usage = getattr(response, "usage", None)
        LOGGER.info(
            "job_extraction_complete",
            extra={
                "message_id": message.message_id,
                "model": self._model,
                "duration_ms": round((monotonic() - started) * 1000, 2),
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "confidence": opportunity.confidence,
                "job_related": opportunity.job_related,
            },
        )
        return opportunity
