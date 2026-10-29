# Output contracts

Every task must contain a non-empty string `task_id`. The pipeline copies that ID into the result; a model candidate may omit it. If a candidate includes a different ID, processing fails.

All successful results are JSON objects with `task_id` and numeric `confidence` in `[0, 1]`.

## Text2SQL

Required candidate fields: `sql`, `rationale`, `confidence`.

Before writing, the pipeline checks that the query is a single read-only SQLite `SELECT` or `WITH` statement and compiles it with `EXPLAIN` against the supplied schema. SQLite—not a keyword regex—parses literals, comments, quoted identifiers, functions, and statement boundaries. An authorizer denies actual write, schema, PRAGMA, attach, and transaction actions.

## Code Author

Required candidate fields: `code`, `rationale`, `confidence`.

Before writing, the pipeline parses the source, checks the requested top-level entry function, rejects forbidden imports, and executes supplied samples in independent subprocesses with a bounded timeout. Candidate stdout and stderr are returned as diagnostic fields and do not share the worker's machine-readable channel.

## Bug Hunter

Required fields: `verdict`, `bugs`, `confidence`. A clean verdict requires no bugs; a buggy verdict requires at least one. Locations must be positive, ordered, and within the submitted source.

Semantic bug accuracy remains a model-evaluation concern; schema validation cannot establish that a reported bug is true.

## Code Reviewer

The deterministic reviewer does not accept model findings. It derives `verdict`, `findings`, and `confidence` from the task source using the documented static rules.

## Hermes finalization

The Hermes runner treats the result file as untrusted. Text2SQL and Code Author results pass through the same deterministic pipeline again before `success`; model-provided validation claims are overwritten. Code Reviewer output is recomputed from the original task and must exactly match the result file. Bug Hunter receives structural/source-range validation because semantic bug accuracy is an evaluation concern.

## Failure behavior

Missing files, invalid JSON, non-object roots, type errors, mismatched task IDs, validation failures, subprocess failures, and timeouts produce explicit failures. The target file is written only after all checks pass. Writes use a same-directory temporary file, `fsync`, and `os.replace`.
