# Architecture

## System flow

```text
Gmail
  |
  v
Recent Message Reader
  |
  v
Deterministic Pre-filter
  |
  v
AI Extraction + Source Classification
  |
  +--------------------+
  |                    |
  v                    v
Preference Engine   Source History
  |                    |
  v                    v
Fit Score          Signal Score
  \                    /
   \                  /
    v                v
      Priority Decision
             |
       +-----+-----+---------+
       |           |         |
       v           v         v
   Gmail Labels  SQLite   Daily Report
                             |
                             v
                   Unsubscribe Suggestions
```

## Agent boundary

The agent is responsible for deciding when available tools are required, especially when important information is missing. V1 tools may include:

- `get_recent_emails`
- `get_email`
- `get_preferences`
- `extract_job_information`
- `fetch_job_page`
- `evaluate_job`
- `get_sender_history`
- `label_email`
- `persist_decision`

The agent may not call destructive tools in V1.

## Decision model

Maintain two independent concepts:

### Job Fit Score

Measures whether the job matches the user's criteria.

### Opportunity Signal Score

Measures the likelihood that the outreach deserves prompt attention.

Do not collapse these too early. A 75-fit direct corporate recruiter email may be more actionable than a 90-fit generic digest item.

## Recommended priority levels

- `URGENT_DIRECT_OUTREACH`
- `HIGH`
- `NORMAL`
- `LOW`

## Critical unknown policy

If any user-configured hard requirement is unknown, classification defaults to `NEEDS_REVIEW` unless another known hard failure already causes `REJECT`.
