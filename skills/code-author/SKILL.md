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

1. Implement the exact `constraints.entry_function` using only allowed imports.
2. Send a JSON candidate through stdin to `python3 scripts/run.py`. Fields are `code`, `rationale`, and `confidence`; omit `task_id` because the toolkit binds it from the original task.
3. Preserve quotes and newlines using JSON encoding, not command-line string interpolation.
4. If deterministic validation fails, revise once. After two failed submissions, surface the validator error.

## Verification

The shared toolkit parses Python syntax, verifies the entry function and forbidden imports, and runs declared samples in separate subprocesses with timeouts before atomically writing the result.

The subprocess boundary prevents a candidate from polluting the validator process and limits hangs. It is not a security sandbox for hostile code.

## Boundaries

This skill generates a single function-sized solution. It does not edit repositories, install dependencies, or claim correctness beyond the supplied deterministic samples.
