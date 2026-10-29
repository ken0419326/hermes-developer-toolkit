# Portfolio refactor changes

This repository was rebuilt beside the original course project rather than rewriting its history.

## Repeatable evaluation harness

- Added 40 public synthetic tasks, balanced across four skills, and a fixed-seed repeated-run plan (120 agent invocations by default).
- Added multi-fixture SQL result checks, extra Python functional/non-mutation samples, controlled defect oracles, and independently authored static-rule gold findings.
- Added atomic checkpoints, exclusive writer locks, strict resume identity checks, execution budgets, and failure-preserving summaries with per-skill success, repeat stability, latency, and bug-verdict metrics.
- Left first-candidate success, internal candidate counts, token cost, effective model identity, and automatic tool-call proof explicitly unmeasured.
- Added offline evaluator regression tests and a documented pilot/formal protocol. No large-suite live result is claimed.

## Live verification record

- On 2026-10-29, exercised commit `3143086bfcb18d679ea971ce19c19daef945477b` with Hermes v0.16.0, provider `openai-codex`, and model `gpt-6-luna`.
- Passed five real-model smoke cases across the four independent skills: Text2SQL, Code Author, Bug Hunter with buggy and correct inputs, and Code Reviewer. No fixture or mock substituted for these live executions.
- Published a sanitized evidence record with per-case checks and elapsed times. Raw session exports, credentials, local configuration, private paths, and original conversation content are not published.
- Kept `designated_tool_call_proven` false. Manual trace review confirmed terminal calls, but that is not automated proof from the verifier.
- Recorded that the buggy Bug Hunter case passed on its third internal candidate submission after two contract failures, without an outer verifier retry, and that the clean case's simple `printf` path does not establish arbitrary shell-content safety.
- These five smoke cases are distinct from the offline suite and the historical course Text2SQL 29/30 result; they do not establish general accuracy, production reliability, or a chained generate-review-repair workflow.

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

