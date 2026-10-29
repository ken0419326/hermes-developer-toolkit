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

Run `python3 scripts/run.py`. Do not manufacture findings in chat and do not pass a model-generated candidate.

## Verification

The reviewer parses the source and emits deterministic findings for its documented rule set. Repeated identical inputs produce identical JSON content.

## Boundaries

This is deliberately a small static analyzer, not a general proof of correctness. It checks syntax errors, dynamic execution calls, potentially unguarded constant indexing, and a context-qualified range boundary pattern. Medium-certainty findings require human review. It does not execute submitted code by default.
