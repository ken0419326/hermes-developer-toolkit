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
2. Use the original submitted program's 1-based source line numbers. Every bug
   requires both `line_start` and `line_end`; `line` is not a valid substitute.
   Allowed severities are `critical`, `high`, `medium`, `low`, and `info`.
   Allowed bug types are `api_misuse`, `edge_case`, `logic_error`,
   `null_deref`, `off_by_one`, `type_error`, `unhandled_input`, and
   `unsafe_operation`. Choose the closest supported value without inventing a
   new label.
3. Write `verdict`, `bugs`, and `confidence` as JSON to `HERMES_TOOLKIT_CANDIDATE_PATH`; omit `task_id`. Use a quoted literal heredoc, then invoke the absolute skill script:

   ```bash
   cat > "$HERMES_TOOLKIT_CANDIDATE_PATH" <<'HERMES_CANDIDATE_JSON'
   {
     "verdict": "buggy",
     "bugs": [
       {
         "line_start": 3,
         "line_end": 3,
         "severity": "medium",
         "type": "logic_error",
         "description": "The returned value contradicts the stated behavior for a valid input."
       }
     ],
     "confidence": 0.8
   }
   HERMES_CANDIDATE_JSON
   python3 "${HERMES_SKILL_DIR}/scripts/run.py" --candidate "$HERMES_TOOLKIT_CANDIDATE_PATH"
   ```

   The quoted delimiter prevents shell expansion of candidate content.
4. If validation fails, use the error message to check the entire candidate,
   including every required field and enum value, before resubmitting. Do not
   stop after fixing only the first reported error, and do not invent a defect
   merely to satisfy the schema.

## Verification

The toolkit binds the original task ID, checks all fields and source ranges, enforces verdict/report consistency, and atomically writes only valid results. `${HERMES_SKILL_DIR}` makes the command independent of the current working directory.

## Boundaries

The LLM performs the semantic comparison. Contract validation does not prove that every reported bug is correct, so real-model accuracy must be evaluated separately.
