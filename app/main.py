import argparse
import json
import logging
from pathlib import Path
from typing import Sequence

from app.agent.orchestrator import JobTriageOrchestrator
from app.config import Settings, load_preferences
from app.models.domain import JobOpportunity
from app.models.email import EmailMessage
from app.services.evaluation import evaluate_job
from app.services.openai_extractor import OpenAIJobExtractor
from app.tools.gmail import GmailEmailReader, create_gmail_service


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Job opportunity email triage")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="Read and normalize recent Gmail messages")
    scan.add_argument("--hours", type=int, help="Lookback window in hours")
    scan.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Do not perform side effects (the Day 1 scan is always read-only)",
    )
    scan.add_argument(
        "--preferences",
        type=Path,
        default=Path("config/preferences.yaml"),
        help="Path to preferences YAML",
    )
    extract = subparsers.add_parser(
        "extract", help="Extract structured job facts from a saved email fixture"
    )
    extract.add_argument("--file", type=Path, required=True, help="Email fixture JSON")
    extract.add_argument(
        "--max-input-chars",
        type=int,
        default=20_000,
        help="Maximum body characters sent to the model",
    )
    evaluate = subparsers.add_parser(
        "evaluate", help="Evaluate a saved job opportunity deterministically"
    )
    evaluate.add_argument(
        "--opportunity", type=Path, required=True, help="JobOpportunity JSON file"
    )
    evaluate.add_argument(
        "--preferences",
        type=Path,
        default=Path("config/preferences.yaml"),
        help="Path to preferences YAML",
    )
    process = subparsers.add_parser(
        "process", help="Extract and evaluate one saved email through the bounded agent"
    )
    process.add_argument("--file", type=Path, required=True, help="Email fixture JSON")
    process.add_argument(
        "--preferences",
        type=Path,
        default=Path("config/preferences.yaml"),
        help="Path to preferences YAML",
    )
    process.add_argument(
        "--max-iterations",
        type=int,
        default=4,
        help="Maximum number of bounded tool calls",
    )
    process.add_argument(
        "--max-input-chars",
        type=int,
        default=20_000,
        help="Maximum email body characters sent to the model",
    )
    process.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Keep all side effects disabled (always enabled for Day 4)",
    )
    return parser


def _print_message(message: EmailMessage) -> None:
    output = message.model_dump(
        mode="json", exclude={"body_text"}, exclude_none=True
    )
    print(json.dumps(output, ensure_ascii=False))


def _load_email_fixture(path: Path) -> EmailMessage:
    if not path.is_file():
        raise FileNotFoundError(f"Email fixture not found: {path}")
    try:
        return EmailMessage.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"Invalid email fixture {path}: {exc}") from exc


def _load_opportunity(path: Path) -> JobOpportunity:
    if not path.is_file():
        raise FileNotFoundError(f"Job opportunity file not found: {path}")
    try:
        return JobOpportunity.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"Invalid job opportunity {path}: {exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.command == "scan":
        preferences = load_preferences(args.preferences)
        hours = args.hours or preferences.gmail.lookback_hours
        if hours < 1:
            raise ValueError("--hours must be at least 1")
        service = create_gmail_service(
            settings.gmail_credentials_file, settings.gmail_token_file
        )
        messages = GmailEmailReader(service).get_recent_emails(hours)
        for message in messages:
            _print_message(message)
        logging.getLogger(__name__).info(
            "scan_complete",
            extra={"message_count": len(messages), "hours": hours, "dry_run": True},
        )
        return 0

    if args.command == "extract":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for live fixture extraction.")
        if not settings.openai_model:
            raise ValueError("OPENAI_MODEL is required for live fixture extraction.")
        from openai import OpenAI

        message = _load_email_fixture(args.file)
        extractor = OpenAIJobExtractor(
            client=OpenAI(api_key=settings.openai_api_key),
            model=settings.openai_model,
            max_input_chars=args.max_input_chars,
        )
        opportunity = extractor.extract(message)
        print(opportunity.model_dump_json(indent=2))
        return 0

    if args.command == "evaluate":
        opportunity = _load_opportunity(args.opportunity)
        preferences = load_preferences(args.preferences)
        result = evaluate_job(opportunity, preferences)
        print(result.model_dump_json(indent=2))
        return 0

    if args.command == "process":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for live fixture processing.")
        if not settings.openai_model:
            raise ValueError("OPENAI_MODEL is required for live fixture processing.")
        from openai import OpenAI

        message = _load_email_fixture(args.file)
        preferences = load_preferences(args.preferences)
        extractor = OpenAIJobExtractor(
            client=OpenAI(api_key=settings.openai_api_key),
            model=settings.openai_model,
            max_input_chars=args.max_input_chars,
        )
        state = JobTriageOrchestrator(
            extractor,
            preferences,
            max_iterations=args.max_iterations,
            dry_run=True,
        ).process(message)
        print(state.model_dump_json(indent=2))
        return 0 if state.status.value == "COMPLETED" else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
