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

1. Read the authoritative task with `python3 -m json.tool "$HERMES_TOOLKIT_TASK_PATH"`. Compare that code with the stated behavior. Report correctness defects, not style preferences.
2. Use 1-indexed source locations and only supported severities and bug types.
3. Write `verdict`, `bugs`, and `confidence` as JSON to `HERMES_TOOLKIT_CANDIDATE_PATH`; omit `task_id`. Use a quoted literal heredoc, then invoke the absolute skill script:

   ```bash
   cat > "$HERMES_TOOLKIT_CANDIDATE_PATH" <<'HERMES_CANDIDATE_JSON'
   {"verdict":"clean","bugs":[],"confidence":0.8}
   HERMES_CANDIDATE_JSON
   python3 "${HERMES_SKILL_DIR}/scripts/run.py" --candidate "$HERMES_TOOLKIT_CANDIDATE_PATH"
   ```

   The quoted delimiter prevents shell expansion of candidate content.
4. If the validator rejects the report, fix its structure once. Do not invent a defect merely to satisfy the schema.

## Verification

The toolkit binds the original task ID, checks all fields and source ranges, enforces verdict/report consistency, and atomically writes only valid results. `${HERMES_SKILL_DIR}` makes the command independent of the current working directory.

## Boundaries

The LLM performs the semantic comparison. Contract validation does not prove that every reported bug is correct, so real-model accuracy must be evaluated separately.
