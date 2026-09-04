# Job Opportunity Agent

A Codex-friendly Python project for building a practical AI agent that scans recent job-related email, extracts opportunity details, evaluates fit, prioritizes direct recruiter outreach, learns source quality over time, recommends unsubscribe actions for consistently irrelevant sources, applies Gmail labels, and generates a daily report.

## MVP goals

- Scan Gmail for the previous 24 hours.
- Detect job/recruiter-related messages.
- Extract structured job information.
- Classify sender/source type.
- Evaluate job fit against configurable preferences.
- Calculate an opportunity-signal score for direct outreach.
- Label email as Strong Match, Possible Match, Needs Review, Rejected, or Direct Outreach.
- Track sender quality over time.
- Recommend unsubscribe for consistently poor sources; never unsubscribe automatically in V1.
- Generate a daily summary report.
- Store feedback for future preference learning.

## Non-goals for V1

- Automatic job applications.
- Automatic recruiter replies.
- Automatic unsubscribe or destructive actions.
- Multi-agent orchestration.
- Vector database/RAG platform.
- Production-grade web UI.

## Quick start

1. Create and activate a Python virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies and verify the project:

   ```powershell
   python -m pip install -r requirements.txt
   python -m pytest
   ```

3. Copy the example configuration files:

   ```powershell
   Copy-Item config\preferences.example.yaml config\preferences.yaml
   Copy-Item .env.example .env
   ```

4. In Google Cloud, enable the Gmail API and create OAuth credentials for a
   Desktop application. Download that file as `credentials.json` in the project
   root. Both `credentials.json` and the generated `token.json` are ignored by
   Git.

5. Run the read-only Day 1 scan:

   ```powershell
   python -m app.main scan --hours 24 --dry-run
   ```

   On the first run, Google opens a browser for authorization. The application
   requests only the `gmail.readonly` scope. The command prints normalized JSON
   metadata and short body previews; it does not label or modify messages.

6. Continue with the implementation plan in `docs/IMPLEMENTATION_PLAN.md`.

## Day 1 implementation

The current read-only ingestion slice includes:

- typed environment settings and validated YAML preferences
- a provider-independent normalized email model
- Gmail OAuth using the read-only scope
- paginated recent-message retrieval
- plain-text, HTML, and multipart body normalization
- a mockable email-reader boundary
- a dry-run scan CLI that omits full message bodies from output

Live Gmail access requires a local OAuth `credentials.json`. Automated tests use
mocks and do not access Gmail or require credentials.

## Day 2 structured extraction

Day 2 adds a bounded OpenAI extraction service that uses Pydantic Structured
Outputs. The model extracts supported facts and source type; it does not score or
make the final preference decision. Requests use `store=False`, message bodies
are capped at 20,000 characters by default, and the trusted local message ID
overrides any ID returned by the model.

Configure a model available to your OpenAI API account in `.env`:

```env
OPENAI_API_KEY=
OPENAI_MODEL=
```

Then extract a synthetic fixture:

```powershell
python -m app.main extract --file tests/fixtures/direct_recruiter.json
```

This command makes a billable OpenAI API request. Automated tests mock the API
and require neither an API key nor network access. Critical facts that are not
stated remain `UNKNOWN` or `null`.

## Day 3 deterministic evaluation

Day 3 evaluates a validated `JobOpportunity` against YAML preferences without
calling Gmail, OpenAI, or any other external service:

```powershell
python -m app.main evaluate `
  --opportunity tests/fixtures/opportunities/strong_match.json `
  --preferences config/preferences.example.yaml
```

The evaluator produces a normalized fit score, typed decision and priority,
reasons, concerns, critical unknowns, and an itemized score breakdown. H1B
support, allowed employment types, and acceptable work modes are enforced as
hard constraints. A known hard failure produces `REJECT`; an unresolved hard
requirement produces `NEEDS_REVIEW`. Location and compensation affect scoring
but are not hard rejection rules.

## Recommended development mode

Build vertically. Complete one end-to-end slice before adding the next capability:

`Gmail -> Extract -> Evaluate -> Label -> Persist -> Report`

Then add source intelligence, unsubscribe recommendations, and research.
