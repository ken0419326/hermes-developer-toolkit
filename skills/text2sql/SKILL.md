---
name: text2sql
description: Generate one read-only SQLite query and submit it through the toolkit validator.
version: 1.0.0
metadata:
  hermes:
    category: data
    requires_toolsets: [terminal]
---

# Text2SQL

## When to Use

Use for a task containing `task_id`, `question`, `db_schema`, and `dialect=sqlite`.

## Procedure

1. Read the task supplied by Hermes. Use only the given schema.
2. Derive one read-only SQLite query. Do not execute or reveal it in chat.
3. Send a JSON candidate without `task_id` to the validator through stdin:

   ```bash
   printf '%s' '<candidate-json>' | python3 scripts/run.py
   ```

   Candidate fields are `sql`, `rationale`, and `confidence`. Encode the candidate as valid JSON; do not interpolate raw SQL into shell arguments.
4. Stop only after the command reports success. On validation failure, correct the query and retry at most once. If the second attempt fails, report the tool error without claiming success.

## Verification

The shared toolkit obtains `task_id` from the original task, compiles the query against an in-memory SQLite schema, validates the output contract, and atomically writes the result. Chat output is not a result.

## Boundaries

- One SQLite `SELECT` or read-only `WITH` query only.
- No data modification, schema modification, external data, or query execution against production databases.
