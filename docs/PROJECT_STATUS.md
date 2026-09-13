# Project Status

Last updated: 2026-09-05

## Current milestone

Day 4 bounded orchestration is implemented and covered by automated tests. The
remaining external verification activities are a live, read-only Gmail smoke
test and a user-approved OpenAI fixture/process run.

## Completed

- Python virtual environment created with Python 3.13.14.
- Project dependencies installed.
- Typed environment settings implemented with Pydantic Settings.
- YAML preferences loading and validation implemented.
- Provider-independent normalized email model added.
- Mockable read-only email-reader interface added.
- Gmail OAuth adapter implemented using only the `gmail.readonly` scope.
- Paginated recent-message retrieval implemented.
- Plain-text, HTML, and multipart Gmail body normalization implemented.
- Missing and malformed message fields handled safely.
- Dry-run scan CLI implemented:

  ```powershell
  python -m app.main scan --hours 24 --dry-run
  ```

- CLI output excludes full email bodies and prints normalized metadata and short
  previews.
- README updated with environment, OAuth, test, and scan instructions.
- Day 2 structured extraction boundary implemented behind a mockable interface.
- OpenAI Responses API integration uses Pydantic Structured Outputs and
  `store=False`.
- Trusted local message IDs override model-returned IDs.
- Model input bodies are bounded to 20,000 characters by default.
- Explicit `EmploymentType` and `WorkMode` enums include `UNKNOWN`.
- Empty messages bypass the model; ambiguous messages remain eligible for model
  review.
- Non-job results cannot retain unsupported job-specific claims.
- Synthetic fixtures cover direct recruiter, staffing agency, LinkedIn alert,
  company alert, unrelated email, and missing critical facts.
- Local fixture extraction CLI implemented:

  ```powershell
  python -m app.main extract --file tests/fixtures/direct_recruiter.json
  ```

- API failure, missing parsed output, input bounding, identity override, and
  critical-unknown paths are tested.
- Pure `JobOpportunity + Preferences -> EvaluationResult` service implemented.
- H1B support, employment type, and work mode are enforced as deterministic hard
  constraints.
- Known hard failures take precedence over critical unknowns.
- Critical unknowns route to `NEEDS_REVIEW` when no hard failure exists.
- Role, employment, visa, location, work mode, and compensation produce
  explainable score components.
- Scores are normalized to 0-100 even when configured weights do not total 100.
- Typed priority values replace free-form priority strings.
- Strong and possible threshold comparisons are inclusive.
- Local evaluation CLI and strong, possible, review, and rejection fixtures
  added.
- Typed in-memory agent state, stages, run statuses, and sanitized tool traces
  implemented.
- Allow-listed tool registry rejects unknown and duplicate tools.
- Dry-run blocks tools marked as side-effecting before their handlers execute.
- Bounded state machine connects extraction and deterministic evaluation.
- Maximum-iteration, tool-failure, invalid-output, and message-ID mismatch paths
  fail closed.
- Raw email bodies, subjects, exception messages, and arbitrary objects are not
  copied into tool traces.
- Combined `process` CLI implemented and forced to dry-run mode.
- Day 4 architecture and safe-extension guidance documented in
  `docs/DAY4_ORCHESTRATION.md`.
- Automated test suite passes: **53 tests passed**.

## Safety status

- Gmail access is read-only.
- No automatic unsubscribe functionality exists.
- No message deletion, archive, reply, recruiter response, or job application
  functionality exists.
- `.env`, `credentials.json`, `token.json`, `.venv`, and SQLite database files
  are excluded by `.gitignore`.

## Missing local setup

The following local files were not present at the last verification:

- `config/preferences.yaml`
- `credentials.json`
- `token.json`

Create the preferences file from the tracked example:

```powershell
Copy-Item config\preferences.example.yaml config\preferences.yaml
```

Obtain `credentials.json` by enabling the Gmail API and downloading OAuth
credentials for a Desktop application from Google Cloud. `token.json` will be
created after the user approves the first browser OAuth flow.

These files contain local configuration or credentials and must not be
committed.

## Known limitations and unverified behavior

- Gmail integration is tested with mocked API responses but has not been tested
  against the user's live Gmail account.
- Real Gmail messages may reveal additional MIME structures that require
  normalization adjustments.
- SQLite models, repositories, and migrations are not implemented yet.
- Live OpenAI extraction has not been run; automated tests use mocked responses.
- Source-signal scoring, persistence, labeling, reporting, and feedback are not
  implemented yet.
- The project is now a Git repository. The last observed commit before Day 4
  implementation was `1f2323b initial commit`.

## Next actions

1. Create `config/preferences.yaml` from the example.
2. Add the local Google OAuth `credentials.json`.
3. Run the live read-only scan:

   ```powershell
   .\.venv\Scripts\python.exe -m app.main scan --hours 24 --dry-run
   ```

4. Confirm that authorization requests only read-only Gmail access.
5. Inspect normalized output for plain-text, HTML, and multipart messages.
6. Add regression tests for any Gmail payload edge cases found during the smoke
   test.
7. Add `OPENAI_API_KEY` and `OPENAI_MODEL` locally, then run one user-approved
   live extraction against a synthetic fixture.
8. Run one user-approved live `process` command against a synthetic fixture.
9. Begin Day 5: source intelligence and direct-outreach prioritization.

## Day 5 target

Implement deterministic source-signal scoring while keeping it separate from
job-fit scoring. Add direct-company recruiter heuristics, LinkedIn direct versus
alert handling, personalized/profile-reference signals, typed priority policy,
and explainable signal components. Do not apply Gmail labels yet; labeling and
persistence remain Day 6.

## Resume instructions

At the beginning of the next work session:

1. Read `AGENTS.md`.
2. Read this file.
3. Review `docs/IMPLEMENTATION_PLAN.md` for the active milestone.
4. Run:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   ```

5. Check the working tree before editing so unrelated user changes are
   preserved.
