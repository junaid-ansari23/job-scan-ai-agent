# One-Week Implementation Plan

## Day 1 — Repository, domain models, Gmail read-only integration

### Deliverables

- Python project bootstrapped.
- Environment/config loading.
- Pydantic domain models.
- Gmail OAuth and read-only email retrieval.
- CLI command to list emails from the last 24 hours.
- Unit tests for message normalization.

### Codex task prompt

Implement Day 1 from this plan. Follow `AGENTS.md`. Create the smallest end-to-end Gmail read path. Do not add LLM calls yet. Add tests and update README with setup instructions.

### Exit criteria

`python -m app.main scan --hours 24 --dry-run` prints normalized email metadata/body previews without modifying Gmail.

---

## Day 2 — AI structured extraction and source classification

### Deliverables

- `JobOpportunity` schema.
- `SourceType` enum.
- LLM prompt and structured output parsing.
- Missing/unknown values handled explicitly.
- Test fixtures covering company recruiter, staffing mailer, LinkedIn alert, and non-job email.

### Codex task prompt

Implement structured extraction and source classification. Use Pydantic validation. Never invent visa, employment type, salary, or location. Represent unavailable values explicitly. Add unit tests using mocked model responses.

### Exit criteria

A local command can process saved email fixtures and print validated JSON.

---

## Day 3 — Preference engine and deterministic scoring

### Deliverables

- Load `preferences.yaml`.
- Hard-constraint evaluation.
- Fit score.
- Decision enum.
- Explanation/reason model.
- Unit tests for boundaries and unknown critical fields.

### Codex task prompt

Implement a pure deterministic evaluation service. The LLM must not decide final hard-constraint outcomes. Add tests for H1B required, employment type, location preference, role preference, and unknown critical fields.

### Exit criteria

Given `JobOpportunity + Preferences`, evaluation is deterministic and fully testable without external APIs.

---

## Day 4 — Agent loop and bounded tools

### Deliverables

- Tool registry.
- Agent state model.
- Tool execution loop.
- Maximum-iteration guard.
- Structured trace logging.
- Dry-run mode for all side effects.

### Codex task prompt

Implement a minimal custom tool-calling agent loop without LangChain or CrewAI. The model may choose among registered read/evaluation tools. Side-effect tools must honor dry-run. Persist a concise tool trace for debugging.

### Exit criteria

The agent can choose `get_email -> extract -> get_preferences -> evaluate` and terminate successfully.

---

## Day 5 — Source intelligence and direct outreach alerts

### Deliverables

- Signal score service.
- Direct company recruiter detection heuristics.
- LinkedIn direct-vs-alert classification.
- Priority model.
- `Jobs/Direct-Outreach` labeling policy.
- Tests for personalized vs bulk message signals.

### Codex task prompt

Add source intelligence. Keep fit score and signal score separate. Prioritize direct company recruiter and LinkedIn direct outreach when sufficiently relevant. Build explainable score components and tests.

### Exit criteria

Daily output clearly surfaces direct outreach separately from generic high-fit opportunities.

---

## Day 6 — Persistence, sender history, unsubscribe recommendations, Gmail labels

### Deliverables

- SQLite schema/repositories.
- Processed-message idempotency.
- Sender stats aggregation.
- Configurable unsubscribe recommendation policy.
- Gmail label creation/application.
- No automatic unsubscribe.

### Codex task prompt

Implement SQLite persistence and sender history. Add configurable unsubscribe recommendation logic based only on accumulated evidence. Add Gmail labeling behind dry-run and explicit configuration. Never implement automatic unsubscribe.

### Exit criteria

Re-running the same scan does not duplicate processing. Poor-quality sources can produce explainable unsubscribe suggestions.

---

## Day 7 — Daily report, feedback, evaluation, hardening

### Deliverables

- Markdown/console daily report.
- Feedback capture CLI.
- Historical evaluation fixture set.
- Metrics summary.
- Error-path tests.
- Documentation cleanup.

### Codex task prompt

Finish the MVP. Add a daily report with direct outreach, strongest matches, needs review, and unsubscribe suggestions. Add simple feedback capture. Create an evaluation harness for labeled fixtures and document known limitations.

### Exit criteria

One command scans, classifies, labels, persists, and reports while safely handling failures and unknowns.

---

# Post-MVP backlog

1. Fetch linked job descriptions when URL is present.
2. Public web/company-career-page research for missing fields.
3. Resume-to-job comparison.
4. Recruiter response drafting with approval.
5. Preference suggestions learned from explicit feedback.
6. LinkedIn integration where technically and legally appropriate.
7. Web dashboard.
