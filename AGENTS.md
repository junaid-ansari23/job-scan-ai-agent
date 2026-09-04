# Codex Instructions — Job Opportunity Agent

## Project mission

Build a small, testable, observable AI agent that helps a user triage job-related messages. The system must combine LLM-based understanding with deterministic rules and bounded tool use.

## Architectural principles

1. **LLM extracts and interprets; code enforces business rules.**
   - Do not let the model silently decide hard requirements such as H1B eligibility.
   - Use explicit enums such as `SUPPORTED`, `NOT_SUPPORTED`, and `UNKNOWN`.

2. **Unknown is a first-class value.**
   - Never infer critical missing facts.
   - Critical unknowns should route to `NEEDS_REVIEW`.

3. **Prefer one tool-using agent over multiple agents for V1.**

4. **All side effects are bounded.**
   - Gmail labeling is allowed after classification.
   - Unsubscribe, delete, archive, send, or reply actions require explicit user approval and are not part of V1 automation.

5. **Every decision must be explainable.**
   - Persist evidence, score components, source type, confidence, and reason summaries.

6. **Idempotency matters.**
   - The same email should not be processed repeatedly unless explicitly re-run.

7. **Favor simple dependencies.**
   - Python, Pydantic, Gmail API, SQLite, pytest.
   - Avoid LangChain/CrewAI initially unless explicitly requested later.

## Coding conventions

- Python 3.12+.
- Type hints everywhere practical.
- Pydantic models for all LLM inputs/outputs and persisted domain structures.
- Small pure functions for scoring and rule evaluation.
- Tool adapters behind interfaces so they can be mocked.
- No secrets in source control.
- Configuration comes from `.env` and YAML.
- Use structured logging.
- Add unit tests with each feature.

## Package responsibilities

- `app/models`: domain and schema models.
- `app/tools`: external tool adapters such as Gmail and web/job-page fetch.
- `app/services`: extraction, scoring, source intelligence, reporting.
- `app/agent`: agent loop, tool registry, orchestration state.
- `app/storage`: SQLite repository and migrations/bootstrap.

## Required V1 labels

- `Jobs/Direct-Outreach`
- `Jobs/Strong-Match`
- `Jobs/Possible-Match`
- `Jobs/Needs-Review`
- `Jobs/Rejected`
- `Jobs/Processed`

## Safety / approval rules

Codex must not implement automatic unsubscribe, message deletion, recruiter reply sending, or job application without a separate explicit task that includes an approval workflow.

## Definition of done for each task

- Feature implemented.
- Unit tests added.
- Error/unknown path handled.
- README or docs updated if behavior changes.
- No secrets or personal data committed.
