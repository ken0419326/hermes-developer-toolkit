---
name: bug-hunter
description: Review Python against a task specification and submit a validated, structured bug report.
version: 1.0.0
metadata:
  hermes:
    category: code
    requires_toolsets: [terminal]
---

# Bug Hunter

## When to Use

Use when a task contains Python `code`, its intended behavior, and optional constraints or examples.

## Procedure

1. Compare the code with the stated behavior. Report correctness defects, not style preferences.
2. Use 1-indexed source locations and only supported severities and bug types.
3. Submit `verdict`, `bugs`, and `confidence` as JSON through stdin to `python3 scripts/run.py`; omit `task_id`.
4. If the validator rejects the report, fix its structure once. Do not invent a defect merely to satisfy the schema.

## Verification

The toolkit binds the original task ID, checks all fields and source ranges, enforces verdict/report consistency, and atomically writes only valid results.

## Boundaries

The LLM performs the semantic comparison. Contract validation does not prove that every reported bug is correct, so real-model accuracy must be evaluated separately.
