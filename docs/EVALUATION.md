# Repeatable real-Hermes evaluation

This protocol extends the five-case live smoke check with a **public synthetic
regression suite**: 40 distinct tasks, 10 per skill, each run three times by
default. It is not an external benchmark, a sealed held-out set, or a production
reliability claim.

## Recorded 2026-10-29 baseline

The frozen program commit
`1414714f21034177d3b663b3f6d443f72b7011ed` completed all 120 planned real-model
agent invocations with Hermes v0.16.0, requested model `gpt-6-luna`, and
user-supplied provider label `openai-codex`. The label and model string are
metadata, not backend attestation. No fixture or mock replaced live execution.

| Scope | Passed | Recorded | Success rate | Tasks passing all three repeats |
| --- | ---: | ---: | ---: | ---: |
| Overall | 114 | 120 | 95% | 37/40 |
| Text2SQL | 30 | 30 | 100% | 10/10 |
| Code Author | 30 | 30 | 100% | 10/10 |
| Code Reviewer | 30 | 30 | 100% | 10/10 |
| Bug Hunter | 24 | 30 | 80% | 7/10 |

Each repeat was 38/40. Overall recorded latency had a 16.330-second median and
35.837-second p95; the 120 recorded durations summed to 2334.982 seconds.
Latency includes agent execution and local grading.

For Bug Hunter, 9 of the 15 known-buggy runs produced a correct validated
report, while all 15 known-clean runs passed. Binary verdict metrics among the
24 graded runs were TP=9, FP=0, FN=0, and TN=15. Thus recall among graded runs
was 100%, but it must always be reported with the six ungraded `invalid_result`
failures; the end-to-end known-buggy success count is 9/15, not 15/15.

Hermes session records directly explained all six failures, so no diagnostic
reproduction was run. Each agent called the Bug Hunter wrapper, corrected an
initial `line` versus `line_start`/`line_end` contract error, but ended with an
unsupported type synonym and no valid result. The original failures were not
deleted, replaced, or retried. Details are in the sanitized
[failure analysis](../artifacts/formal-evaluation-failure-analysis-2026-10-29.md).

Published artifacts and hashes:

- Sanitized baseline: [`artifacts/formal-evaluation-baseline-2026-10-29.json`](../artifacts/formal-evaluation-baseline-2026-10-29.json), SHA-256 `3318d7b77caca39497adf5a1a74d4ae55db9e4aa30dd66c0e9103227850495b4`.
- Sanitized failure analysis: [`artifacts/formal-evaluation-failure-analysis-2026-10-29.md`](../artifacts/formal-evaluation-failure-analysis-2026-10-29.md), SHA-256 `f60d9edcb2c90fc0d8713718dd4e40587d6880b4ea275e13b9a8c3d0607a960b`.
- Preserved ignored raw checkpoint SHA-256: `367ea575d88bc28b3a4d166989ca40a2706aa66f5889adba1bc9326d2f205d37`.
- Preserved ignored raw summary SHA-256: `d6016818188d2f9bc266207571c1c163f5a6733bb35f899b8554984ba0a6be03`.

The raw files contain structured model output and environment metadata and are
not public artifacts. The sanitized files omit private paths, session IDs, and
raw conversation content. This baseline is distinct from the offline suite and
the earlier five-case smoke run.

## Recorded post-fix Bug Hunter regression

After diagnosing the six original failures, commit
`8e6cb0aae4ed6591df9c3a281ae26f841eec27bd` clarified the required location fields,
documented supported enums, and made validator errors list allowed values.
Validation remains strict, with no conversion of unsupported values. The
maintainer reported a separate real-Hermes run on the **same 10 Bug Hunter tasks
with three repeats each**, using the same requested model/provider label, seed
42, and 180-second timeout.

| Metric | Original Bug Hunter baseline | Post-fix same regression set |
| --- | ---: | ---: |
| Passed / recorded | 24/30 | 30/30 |
| Known-buggy correct validated reports | 9/15 | 15/15 |
| Known-clean passes | 15/15 | 15/15 |
| Invalid results / ungraded runs | 6 | 0 |
| Tasks passing all three repeats | 7/10 | 10/10 |
| Unrun invocations | 0 | 0 |
| Recorded-duration sum | 802.039 s | 584.590 s |
| Median / p95 recorded duration | 21.419 / 56.994 s | 18.032 / 27.377 s |

The post-fix verdict counts were TP=15, FP=0, FN=0, TN=15, with no ungraded
runs. All three rounds were 10/10. There were no resume launches or replacement
runs. The first launch was blocked **before any task invocation or checkpoint**:
`hermes --version` exceeded the evaluator's 10-second preflight timeout during an
update check. After the update cache existed, the same settings completed the
30 planned invocations. This preflight incident is recorded separately from
task execution and is a known compatibility limit.

See the [sanitized post-fix summary](../artifacts/bug-hunter-regression-2026-10-30.json).
Its SHA-256 is `4093c68ea8659c76cb586fcdef308c81281d497e462992b1372a9e29223cd503`.
Its source is the maintainer's local execution report also recorded in PR #2;
it is a summary, not a public checkpoint with all model outputs. The preserved,
ignored raw checkpoint and summary hashes are recorded there. Publishing the
summary does not independently reproduce or regrade the local raw outputs.

This result demonstrates observed improvement on known regression tasks, not
held-out generalization. Guidance and validator feedback changed together, so
the run does not isolate their individual effects or compare against a no-skill
agent. **The complete baseline remains 114/120 (95%)**. No new full 120-run
evaluation is claimed, and the original 90 other-skill runs are not combined
with these 30 post-fix runs. The current offline suite has 176 passing tests;
the baseline's historical 168-test result still belongs to its original commit.

To repeat only this scope from a clean committed checkout, choose a fresh output
file; do not overwrite the historical baseline:

```sh
python scripts/evaluate.py --dry-run --skill bug-hunter --repeats 3
python scripts/evaluate.py --live --model gpt-6-luna \
  --provider-label openai-codex --skill bug-hunter --repeats 3 --seed 42 \
  --timeout 180 --max-invocations 30 --max-wall-seconds 1800 \
  --output outputs/evaluation/bug-hunter-new-regression.json
```

## What is measured

| Skill | Tasks | Independent answer checks |
| --- | ---: | --- |
| Text2SQL | 10 | Execute the candidate and reference query on three data fixtures; compare row bags, preserving duplicates and column order. Cases cover joins, aggregation, HAVING, NULL, anti-joins, zero counts, dates, and maximum ties. |
| Code Author | 10 | Public examples plus 5–6 evaluator-only samples per task; verify returns and input non-mutation in subprocesses. Cases include grouping, rotation, dictionaries, Unicode, intervals, and empty inputs. |
| Bug Hunter | 10 | Five buggy/clean pairs; binary verdict and strict controlled-defect checks using a known source line, accepted types, and English keywords. Extra reports fail strict success. |
| Code Reviewer | 10 | Compare rule id, location, type, multiplicity, and verdict against explicitly authored gold findings. Gold is not generated by the reviewer under test. |

The evaluator sends only the task to Hermes, never the oracle, reference code,
extra samples, data fixtures, or gold query in its task payload. These are public
repository files, however: the terminal agent could inspect them. This is not an
isolation boundary or a contamination-resistant evaluation. Do not call these
samples unseen or held-out. SQL fixtures reduce coincidental correct queries;
they do not prove equivalence on every database.

Code Reviewer is a deterministic rule engine routed through the agent. Its score
measures the documented rules and workflow, not general LLM code-review ability.
Bug Hunter keyword grading can reject semantically correct paraphrases or accept
superficial matches; inspect disagreements, preserve original scores, and report
any later human adjudication separately.

## Prepare and preview (no model calls)

```sh
python -m pip install -e '.[dev]'
python -m pytest -m 'not integration'
python examples/offline_demo.py
python scripts/evaluate.py --dry-run
```

The preview reports 40 tasks and 120 planned **agent invocations**, with zero
actual invocations. One invocation may make several model requests and tool
calls, including candidate corrections. The timeout-only upper bound is six
hours for 120 × 180 seconds, excluding grading. Actual usage/cost cannot be
estimated from invocation count alone. No API keys or credentials are read by
the evaluator; Hermes uses its existing authenticated provider.

## Pilot before the full run

Use a clean checkout, the four repository skills, and the same provider/model
settings throughout. Keep a note of non-secret generation settings; the tool
does not attest effective temperature, provider identity, or the resolved model.

```sh
python scripts/evaluate.py --live --model gpt-6-luna \
  --provider-label openai-codex --repeats 1 --limit-per-skill 1 \
  --output outputs/evaluation/pilot.json --max-invocations 4
```

This pilot is four tasks, not a full evaluation, and does not include all
buggy/clean pairs. Do not combine it with the formal run or tune prompts on the
formal results and still claim an untouched evaluation set.

## Frozen repeated run

Commit any intended code/skill changes before starting; live mode rejects a dirty
tracked worktree or a missing Git commit. Source identity is checked before and
after every invocation; a detected change stops execution and invalidates that
attempt. This detects persistent changes, not transient edits restored before
inspection. Use an explicit model,
fixed source commit, suite, seed, timeout, and repeat count. The model string and
provider label are requested/unverified metadata, not proof of the backend used.

```sh
python scripts/evaluate.py --live --model gpt-6-luna \
  --provider-label openai-codex --repeats 3 --seed 42 \
  --timeout 180 --max-invocations 120 --max-wall-seconds 3600 \
  --output outputs/evaluation/formal.json
```

The execution budget stops starting new invocations after an hour; an active
invocation plus grading may finish later. Three consecutive failures stop the
launch to avoid repeatedly consuming quota on a broken configuration. A partial
run is explicitly marked incomplete; it must not be presented as 120/120.
These launch budgets can be adjusted without changing the evaluation manifest.

Resume after correcting an external availability problem, without changing the
code, skills, Hermes version, Python/SQLite/system versions, model, suite, seed,
timeouts, or repeat count:

```sh
python scripts/evaluate.py --live --model gpt-6-luna \
  --provider-label openai-codex --repeats 3 --seed 42 \
  --timeout 180 --max-invocations 120 --max-wall-seconds 3600 \
  --output outputs/evaluation/formal.json --resume
```

Resume never retries recorded failures. A started invocation is checkpointed
before execution; if interrupted, it remains an interrupted failure. All planned
remaining slots are run at most once. If no result was saved before interruption,
this does not prove that the provider did no work. There is no exactly-once
network guarantee. An exclusive output lock prevents concurrent writers; after
an abrupt process kill, remove a stale `.lock` only after confirming no evaluator
is still running. Changed manifests require a new run, not mixed results.

## Read the report

The checkpoint contains the manifest, plan, final structured outputs, per-run
grades, and failure categories. `formal-summary.json` is regenerated from it.
Outputs default to the already-ignored `outputs/` directory and are not published
automatically. No CLI stdout, stderr, raw session export, or exception message is
saved. Inspect structured model outputs and sanitize before publishing evidence.

Report all of the following together:

- Distinct tasks, planned/recorded/unrun invocations, repeats, and completion.
- Overall and per-skill final task success among recorded attempts, with failures
  included. Preserve interrupted, timeout, invalid-result, and tool-error rows.
- Fraction of fully repeated tasks passing every repetition. Do not count three
  runs of one task as three independent tasks or as a pass@3 score.
- Median and linearly interpolated p95 elapsed time, separately for all timed
  attempts and successful attempts. This includes agent execution **and local
  grading**, not just LLM response time. Small-sample p95 is unstable.
- Bug-verdict TP/FP/FN/TN, precision, recall, specificity, and ungraded runs.
  These binary metrics exclude ungraded runs; task success still counts them as
  failures. Strict defect-localization success is a separate, stronger check.

First-candidate success, candidate submission count, token cost, effective model
identity, and automatic proof of designated tool use remain unmeasured. They are
not inferred from the final result. Hermes can internally correct candidates;
the outer evaluator does not retry. Collect supported structured session traces
in a future change before claiming first-attempt or retry metrics.

The model outputs are nondeterministic. Fixed ordering and frozen inputs make
the procedure repeatable, not bit-for-bit model responses. Repetitions are
correlated, and 40 authored tasks are not representative of all developer work.
No productivity gain or improvement over the previous implementation can be
claimed without a separate controlled baseline using the same frozen tasks.

Generated Python is executed in subprocesses with timeouts, **not a security
sandbox**. Use only controlled inputs and a disposable environment with minimal
privileges; do not use this harness to execute unknown third-party code.

## Offline checks of the evaluator

`tests/test_evaluation.py` validates the gold/reference cases, wrong-answer
rejection, input mutation, SQL duplicates and bounds, failure denominators,
resume behavior, interrupted attempts, locking, and dry-run behavior. Test-double
runs are labeled `offline-harness-test`; they are not live model evidence.
