# Product Requirements — Job Opportunity Agent

## 1. Problem statement

Job seekers often receive a mixture of relevant recruiter outreach, generic job alerts, staffing-agency mailers, and irrelevant opportunities. Manually reviewing all of them creates noise and causes high-value direct recruiter messages to be missed.

The system should act as a bounded AI job-opportunity assistant that reviews recent messages, understands the opportunity and source, evaluates fit, prioritizes direct outreach, tracks source quality, and recommends cleanup actions.

## 2. Primary user outcomes

The user should be able to answer these questions quickly every day:

- Which opportunities are the strongest matches?
- Which messages are direct recruiter outreach and deserve immediate attention?
- Which opportunities need manual review because critical information is missing?
- Which senders repeatedly produce low-quality or irrelevant opportunities?
- Which senders should I consider unsubscribing from?

## 3. Core functional requirements

### FR-1 Recent message ingestion

The system shall retrieve Gmail messages from a configurable lookback window, default 24 hours.

### FR-2 Job-related message detection

The system shall distinguish job/recruiting messages from unrelated email.

### FR-3 Structured opportunity extraction

For a job-related message, extract when available:

- company
- role/title
- seniority
- employment type
- location
- work mode: remote/hybrid/onsite/unknown
- compensation
- visa/H1B sponsorship or transfer support
- recruiter/sender name
- sender organization
- job URL
- source type
- confidence and supporting evidence

### FR-4 Source intelligence

Classify the source as one of:

- `DIRECT_COMPANY_RECRUITER`
- `STAFFING_AGENCY`
- `LINKEDIN_DIRECT_MESSAGE`
- `LINKEDIN_JOB_ALERT`
- `AUTOMATED_MAILER`
- `COMPANY_JOB_ALERT`
- `UNKNOWN`

### FR-5 Fit evaluation

Evaluate the opportunity against configurable hard constraints and preferences.

Output:

- fit score: 0-100
- decision: `STRONG_MATCH`, `POSSIBLE_MATCH`, `NEEDS_REVIEW`, `REJECT`
- reasons
- concerns
- critical unknowns

### FR-6 Opportunity signal evaluation

Calculate a separate signal score reflecting how valuable the outreach itself appears to be.

Positive signals may include:

- direct company recruiter
- company-owned domain
- personalized outreach
- explicit reference to user profile/background
- direct LinkedIn message

Negative signals may include:

- bulk mailer language
- automated digest
- historically poor sender quality

### FR-7 Priority handling

Direct company recruiter and LinkedIn direct outreach that pass minimum relevance checks shall be surfaced in a high-priority section and optionally labeled `Jobs/Direct-Outreach`.

### FR-8 Historical sender quality

Persist sender statistics including:

- total messages analyzed
- job messages
- strong matches
- possible matches
- needs review
- rejected
- rolling match rate
- common rejection reasons
- first seen / last seen

### FR-9 Unsubscribe recommendation

The system shall recommend, but not automatically execute, unsubscribe/block actions when a sender meets configurable poor-quality thresholds.

Example default policy:

- minimum 8 analyzed job messages
- 0 strong matches
- <= 10% strong + possible match rate
- at least 70% rejected

### FR-10 Gmail labeling

Apply configured labels based on classification. The original message remains in Gmail.

### FR-11 Daily report

Generate a report containing:

- total messages processed
- number of job opportunities
- direct outreach alerts
- strong matches
- possible matches
- needs review
- rejected count
- low-quality sender / unsubscribe suggestions

### FR-12 Feedback capture

Allow the user to record feedback such as:

- good recommendation
- bad recommendation
- should have been stronger
- should have been rejected
- incorrect extraction

Feedback is persisted for analysis. V1 does not automatically rewrite user preferences.

## 4. Non-functional requirements

### NFR-1 Explainability

Every classification must include an evidence-based summary and score breakdown.

### NFR-2 Reliability

Processing must be idempotent by Gmail message ID.

### NFR-3 Privacy

Store the minimum email content required. Prefer normalized extracted fields over full message bodies for long-term persistence.

### NFR-4 Observability

Log agent run ID, message ID, tool calls, durations, failures, classification, and token/model metadata when available.

### NFR-5 Cost control

Use deterministic prefilters where practical and avoid repeated LLM calls for already processed messages.

## 5. MVP acceptance criteria

Using at least 30 historical messages, the system can run end-to-end and:

1. Detect job-related messages.
2. Extract structured attributes with no fabricated critical values.
3. Identify direct outreach with useful precision.
4. Apply correct Gmail labels.
5. Produce a readable ranked report.
6. Generate unsubscribe recommendations only from historical evidence.
7. Avoid auto-unsubscribe and auto-reply actions.
