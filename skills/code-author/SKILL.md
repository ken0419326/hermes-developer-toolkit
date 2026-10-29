---
name: code-author
description: Generate a Python function and submit it to deterministic syntax, import, and sample validation.
version: 1.0.0
metadata:
  hermes:
    category: code
    requires_toolsets: [terminal]
---

# Code Author

## When to Use

Use for a task containing a Python `task_description`, `constraints`, and optional `sample_inputs`.

## Procedure

1. Read the original task with `python3 -m json.tool "$HERMES_TOOLKIT_TASK_PATH"`. Implement the exact `constraints.entry_function` using only allowed imports.
2. Write fields `code`, `rationale`, and `confidence` as JSON to `HERMES_TOOLKIT_CANDIDATE_PATH`; omit `task_id`. Use a literal quoted heredoc so the shell does not expand quotes, `$()`, backticks, or Unicode:

   ```bash
   cat > "$HERMES_TOOLKIT_CANDIDATE_PATH" <<'HERMES_CANDIDATE_JSON'
   {"code":"def required(...):\n    ...\n","rationale":"...","confidence":0.8}
   HERMES_CANDIDATE_JSON
   python3 "${HERMES_SKILL_DIR}/scripts/run.py" --candidate "$HERMES_TOOLKIT_CANDIDATE_PATH"
   ```

3. Preserve code newlines with JSON `\n`; never embed Python source in a command-line argument.
4. If deterministic validation fails, revise once. After two failed submissions, surface the validator error.

## Verification

The shared toolkit parses Python syntax, verifies the entry function and forbidden imports, and runs declared samples in separate subprocesses with timeouts before atomically writing the result.

The subprocess boundary prevents a candidate from polluting the validator process and limits hangs. It is not a security sandbox for hostile code.

`${HERMES_SKILL_DIR}` resolves to the absolute skill directory, so execution is independent of the current working directory.

## Boundaries

This skill generates a single function-sized solution. It does not edit repositories, install dependencies, or claim correctness beyond the supplied deterministic samples.
