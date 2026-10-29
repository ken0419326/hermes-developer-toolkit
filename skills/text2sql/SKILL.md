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

1. Read the original task file before reasoning:

   ```bash
   python3 -m json.tool "$HERMES_TOOLKIT_TASK_PATH"
   ```

   Use only the schema in that file. Do not reconstruct the task from chat text.
2. Derive one read-only SQLite query. Do not execute or reveal it in chat.
3. Write a JSON candidate without `task_id` to the runner-provided candidate path using a literal heredoc. A quoted delimiter preserves single quotes, double quotes, Unicode, newlines, `$()`, backticks, and other shell characters without expansion:

   ```bash
   cat > "$HERMES_TOOLKIT_CANDIDATE_PATH" <<'HERMES_CANDIDATE_JSON'
   {"sql":"SELECT ...","rationale":"...","confidence":0.8}
   HERMES_CANDIDATE_JSON
   python3 "${HERMES_SKILL_DIR}/scripts/run.py" --candidate "$HERMES_TOOLKIT_CANDIDATE_PATH"
   ```

   Candidate fields are `sql`, `rationale`, and `confidence`. Encode embedded newlines in JSON strings as `\n`. Never place raw SQL in a command-line argument.
4. Stop only after the command reports success. On validation failure, correct the query and retry at most once. If the second attempt fails, report the tool error without claiming success.

## Verification

The shared toolkit obtains `task_id` from the original task, compiles the query against an in-memory SQLite schema, validates the output contract, and atomically writes the result. The absolute `${HERMES_SKILL_DIR}` token is supplied by Hermes; the procedure does not depend on the session working directory. Chat output is not a result.

## Boundaries

- One SQLite `SELECT` or read-only `WITH` query only.
- No data modification, schema modification, external data, or query execution against production databases.
