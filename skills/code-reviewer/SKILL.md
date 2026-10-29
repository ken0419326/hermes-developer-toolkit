---
name: code-reviewer
description: Run deterministic, explainable static checks over a Python source snippet.
version: 1.0.0
metadata:
  hermes:
    category: code
    requires_toolsets: [terminal]
---

# Code Reviewer

## When to Use

Use for deterministic checks of a Python snippet supplied in the original task.

## Procedure

1. Read the authoritative task with `python3 -m json.tool "$HERMES_TOOLKIT_TASK_PATH"`.
2. Run `python3 "${HERMES_SKILL_DIR}/scripts/run.py"`. Do not manufacture findings in chat and do not pass a model-generated candidate.

## Verification

The reviewer reads source from the original task file, not from model output, and emits deterministic findings for its documented rule set. Repeated identical inputs produce identical JSON content. `${HERMES_SKILL_DIR}` is an absolute path supplied by Hermes, so the command is working-directory independent.

## Boundaries

This is deliberately a small static analyzer, not a general proof of correctness. It checks syntax errors, dynamic execution calls, potentially unguarded constant indexing, and a context-qualified range boundary pattern. Medium-certainty findings require human review. It does not execute submitted code by default.
