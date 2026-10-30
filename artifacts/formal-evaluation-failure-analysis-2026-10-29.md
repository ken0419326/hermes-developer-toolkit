# Formal evaluation failure analysis

This is a sanitized analysis of the six `invalid_result` rows in the 2026-10-29
formal evaluation of commit
`1414714f21034177d3b663b3f6d443f72b7011ed`. The requested model was
`gpt-6-luna` and the unverified provider label was `openai-codex`.

## Evidence and preservation

The ignored raw checkpoint was preserved without modification. Its SHA-256 is
`367ea575d88bc28b3a4d166989ca40a2706aa66f5889adba1bc9326d2f205d37`;
the raw summary SHA-256 is
`d6016818188d2f9bc266207571c1c163f5a6733bb35f899b8554984ba0a6be03`.
Hermes v0.16.0 `sessions export` records contained one matching session for each
original failed task ID. Session IDs, private paths, raw conversations, and
unnecessary environment metadata are omitted here.

No diagnostic reproduction was needed or run. Every finding below is direct
evidence from the original task, terminal calls, submitted candidate JSON, and
wrapper output. No candidate was manually repaired and then counted as an
original success.

## Per-invocation findings

| Task | Repeat | Recorded time | Candidate submissions | Skill wrapper and validator evidence | Same-invocation correction | Why the original run remained invalid | Evidence status |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| `bug-mean-buggy` | 1 | 28.323 s | First used `line: 2`, severity `high`, type `crash`, and a relevant empty-list division description. Second used `line_start: 2` and `line_end: 2` but kept type `crash`. | The Bug Hunter wrapper was called twice. It first returned `line_start must be a positive integer`, then `type is not supported`. | Yes, the source-location fields were corrected once. | `crash` is not a supported contract type; no third valid submission was made. | Direct evidence |
| `bug-mean-buggy` | 2 | 28.839 s | First used `line: 2`, severity `high`, type `runtime_error`, and the same relevant defect. Second corrected the range but retained `runtime_error`. | The wrapper help was inspected, then the Bug Hunter wrapper was called twice and returned the same location and unsupported-type errors in sequence. | Yes, the source-location fields were corrected once. | `runtime_error` is not supported; the invocation ended without a valid result. | Direct evidence |
| `bug-mean-buggy` | 3 | 30.970 s | First used `line: 2`, severity `high`, type `logic`, and a relevant divide-by-zero description. Second corrected the range but retained `logic`. | The wrapper rejected `line_start`; the agent inspected the wrapper and loaded the Bug Hunter skill, then the second wrapper call returned `type is not supported`. | Yes, the source-location fields were corrected once. | `logic` is not the supported enum value `logic_error`; no valid result was written. | Direct evidence |
| `bug-copy-append-buggy` | 1 | 18.677 s | First used `line: 2`, severity `high`, type `side_effect`, and correctly described input mutation. Second corrected the range but retained `side_effect`. | Two Bug Hunter wrapper calls returned the location error followed by the unsupported-type error. | Yes, the source-location fields were corrected once. | `side_effect` is not a supported contract type; no further correction occurred. | Direct evidence |
| `bug-copy-append-buggy` | 3 | 27.706 s | First used `line: 2`, severity `high`, type `mutation`, and correctly described input mutation. Second corrected the range but retained `mutation`; the wrapper source was then inspected. | Two wrapper calls returned the location error followed by the unsupported-type error. | Yes, the source-location fields were corrected once. | `mutation` is not supported, and inspection after the rejection did not produce another candidate. | Direct evidence |
| `bug-all-positive-buggy` | 2 | 32.017 s | First used `line: 2`, severity `high`, type `logic`, and correctly described `any` versus `all`. Second corrected the range but retained `logic`. | The first wrapper call returned the location error. An auxiliary inspection command then had a shell syntax error. The final wrapper call returned `type is not supported`. | Yes, the source-location fields were corrected once. | `logic` is unsupported; the unrelated inspection-command error was not the final validator cause. | Direct evidence |

## Classification

All six candidates were valid JSON and reached field-level contract validation.
All six read the authoritative task and invoked the actual Bug Hunter wrapper.
The candidate omitted `task_id` as intended, allowing the pipeline to bind the
authoritative ID. Severity `high`, confidence values, the corrected line 2
ranges, verdicts, bug arrays, and descriptions were acceptable up to the
reported error.

The direct failure sequence was therefore:

1. Every first candidate used the non-contract field `line` instead of the
   required `line_start` and `line_end` fields.
2. Every agent corrected that error within the same invocation.
3. Every final candidate still used a semantically plausible but unsupported
   type synonym: `crash`, `runtime_error`, `logic`, `side_effect`, or
   `mutation`.
4. The validator rejected the type and no invocation produced the required
   validated result file.

These remain end-to-end failures. The semantically relevant descriptions do
not turn a rejected candidate into a successful model result.

## Minimal corrective direction

The smallest future change is documentation/prompt hardening in the Bug Hunter
skill: explicitly show the required `line_start`/`line_end` fields and enumerate
the accepted types (`api_misuse`, `edge_case`, `logic_error`, `null_deref`,
`off_by_one`, `type_error`, `unhandled_input`, `unsafe_operation`) next to the
candidate example. The current instruction says to use supported values without
listing them, while the wrapper's error also does not return the allowed set.

An optional verifier usability improvement would include the accepted enum in
the rejection message. Neither change should be credited as improving this
frozen baseline without a new, separately labeled evaluation.
