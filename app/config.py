from pathlib import Path

import yaml
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.preferences import Preferences


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and an optional .env."""

    openai_api_key: str | None = None
    openai_model: str | None = None
    gmail_credentials_file: Path = Path("credentials.json")
    gmail_token_file: Path = Path("token.json")
    database_url: str = "sqlite:///data/job_agent.db"
    log_level: str = "INFO"
    dry_run: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_preferences(path: Path) -> Preferences:
    """Load and validate user preferences from YAML."""

    if not path.is_file():
        raise FileNotFoundError(
            f"Preferences file not found: {path}. Copy "
            "config/preferences.example.yaml to config/preferences.yaml."
        )

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in preferences file {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"Preferences file {path} must contain a YAML mapping.")

    try:
        return Preferences.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid preferences in {path}: {exc}") from exc
