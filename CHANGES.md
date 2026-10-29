# Portfolio refactor changes

This repository was rebuilt beside the original course project rather than rewriting its history.

## Reliability

- Replaced four independent output writers with one shared contract and atomic writer.
- Bound result `task_id` to the original task; model candidates no longer need to restate it.
- Moved SQL and Python source through JSON stdin/files instead of shell arguments.
- Added explicit failures for missing files, invalid JSON roots, type mismatches, tool errors, invalid source ranges, and timeouts.
- Connected SQL compilation and Python sample validation to the actual write pipeline.

## Reviewer

- Replaced task-specific line-number shortcuts with AST-based, explainable rules.
- Made `range(len(x)-1)` conditional on an explicit all-items requirement.
- Changed ambiguous findings to medium-certainty review requests.
- Removed default in-process execution of reviewed code.

## Testing and publication

- Replaced stale placeholder paths and old runner imports with standalone tests.
- Added fixture-based offline demos that explicitly do not call a model.
- Separated optional real-Hermes integration tests from offline CI.
- Removed course gold data, reference opponents, private feedback, and gateway-specific configuration.

## Post-publication reliability hardening

- Normalized multiple-statement rejection across supported Python versions by
  handling the `sqlite3.Warning` raised by Python 3.10 as a validation error.

Regression tests were added before implementation changes. The pre-fix run produced **17 failures, 65 passes, and 1 skipped live integration test**. Confirmed failures covered missing final content validation, forged reviewer output, SQL literal/comment false positives, sample stdout protocol corruption, missing diagnostics, task handoff, and working-directory-sensitive wrappers. Live model compliance with the handoff remains an explicitly unverified risk rather than a test result.

After extending the working-directory regression from two wrappers to all four, Code Author exposed one additional confirmed defect: its subprocess used module lookup relative to the caller's environment. The worker now launches through its absolute package file path.

- Re-run SQL/Python mechanical checks after Hermes exits; never trust a model-written `validation` object.
- Recompute Code Reviewer findings from the authoritative task and reject a different result file.
- Replace whole-string SQL keyword/semicolon regexes with SQLite parsing plus an authorizer for real mutation actions.
- Separate candidate stdout/stderr from the sample worker JSON protocol and retain both for debugging.
- Preload the selected skill with `-s`, pass an explicit task-file instruction, and expose task/candidate/output paths through environment variables.
- Use `${HERMES_SKILL_DIR}` and forward wrapper CLI arguments so every skill works outside its own directory.
- Replace shell-interpolated candidate examples with literal-heredoc JSON files passed via `--candidate`.
