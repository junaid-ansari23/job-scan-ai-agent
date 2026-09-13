# Day 4 Orchestration Design

This document explains the bounded orchestration layer and the invariants that
future revisions must preserve.

## Purpose

Day 4 connects the existing extraction and deterministic evaluation components
for one email:

```text
EmailMessage
    |
    v
extract_job_information
    |
    v
JobOpportunity
    |
    v
evaluate_job
    |
    v
EvaluationResult
```

The orchestrator is intentionally a small state machine, not a general workflow
framework. This keeps tool access explicit, execution bounded, and behavior easy
to test.

## Main types

### `AgentState`

`app/agent/models.py` defines the complete state for one message-processing run:

- `run_id`: unique ID for observability
- `message_id`: immutable identity of the source email
- `status`: running, completed, failed, or iteration limit
- `stage`: extraction, evaluation, or finished
- `iteration_count` and `max_iterations`: loop bound
- `dry_run`: side-effect policy passed to every tool call
- `opportunity` and `evaluation`: validated intermediate/final results
- `traces`: sanitized tool execution records
- `error_code` and `error_summary`: safe terminal failure information

The state is currently in memory. SQLite persistence belongs to Day 6.

### `ToolRegistry`

`app/agent/tool_registry.py` is the only route through which the orchestrator
executes registered operations. A `RegisteredTool` declares its name, handler,
and whether it has side effects.

Important registry behavior:

1. Unknown names are rejected.
2. Duplicate names are rejected.
3. A side-effecting tool is blocked before its handler runs when `dry_run=True`.
4. Exceptions become failed invocations instead of escaping the agent loop.
5. Trace summaries are type-aware and never contain raw email bodies, subjects,
   arbitrary input dictionaries, exception messages, secrets, or credentials.

When adding a new domain input/output type, extend `_summarize` with a small
allow list of safe fields. Do not fall back to serializing arbitrary objects.

### `JobTriageOrchestrator`

`app/agent/orchestrator.py` owns state transitions. Day 4 selection is
deterministic:

```text
NEEDS_EXTRACTION -> NEEDS_EVALUATION -> FINISHED
```

Before every tool invocation, the loop checks the maximum iteration count. A
limit therefore stops work before another tool can execute. Every successful
transition also validates the output type. Extraction output must carry the same
message ID as the source email.

## Failure semantics

The orchestrator fails closed:

- tool exception -> `FAILED`
- dry-run block -> `FAILED`
- unexpected output type -> `FAILED`
- mismatched message ID -> `FAILED`
- exhausted iteration budget -> `ITERATION_LIMIT`

Partial state can remain available for diagnosis, but `COMPLETED` is set only
after a validated `EvaluationResult` is produced.

Exception messages are intentionally excluded from state because API/library
errors can echo request data. Detailed exceptions may be sent to a separately
secured logging sink in a future observability task, but must not be placed in
persisted tool traces.

## Dry-run and future side effects

The Day 4 CLI always constructs the orchestrator with `dry_run=True`. Current
tools are extraction and pure evaluation, so neither modifies external state.

When Gmail labeling is introduced later:

1. Register it with `has_side_effects=True`.
2. Keep dry-run as the default.
3. Test that the handler is never called during dry-run.
4. Request only the minimum Gmail scope required for labels.
5. Do not introduce delete, archive, unsubscribe, reply, or apply tools.

## Replacing deterministic selection later

A future model may propose the next tool, but its proposal must still pass
through `ToolRegistry`. Preserve all of these controls:

- allow-listed names
- typed state transitions
- maximum-iteration check before execution
- dry-run enforcement in the registry
- sanitized traces
- validated tool output types
- message identity check

The model should never receive a callable or client object directly.

## Testing guidance

The Day 4 tests use mocked extractors and real deterministic evaluation. They
cover successful processing, non-job processing, tool exceptions, invalid
outputs, message-ID mismatch, iteration exhaustion, unknown tools, duplicate
tools, dry-run blocking, and sensitive-data exclusion.

Run all tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
