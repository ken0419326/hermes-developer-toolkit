# Real-Hermes smoke verification

This opt-in verifier exercises four skills through five independent Hermes
invocations. Bug Hunter has a buggy and a correct example. It adds answer checks
beyond the existing Text2SQL integration test's `run.status` assertion.

## Prerequisites

- Install this package and its development dependencies with `python -m pip install -e '.[dev]'`.
- Install the compatible Hermes CLI described in `HERMES_COMPATIBILITY.md`.
- Configure an existing, authorized model provider in Hermes and load this
  repository's skill directory. The verifier uses that existing configuration;
  it does not create accounts, obtain credentials, or provide a model.
- Use trusted examples only; Python candidate execution is not a hostile-code sandbox.

## Preview without model calls

From the repository root:

```bash
python scripts/verify_live.py --dry-run
python -m pytest tests/test_live_verifier.py -q
```

The unit tests use an explicitly injected test double. Their success does not
establish any real-model result. The default offline CI also runs these tests
without credentials and never invokes the live command.

## Explicitly run real Hermes

After the existing Hermes provider is usable:

```bash
python scripts/verify_live.py --live
# Optional: choose a model already configured in Hermes.
python scripts/verify_live.py --live --model YOUR_CONFIGURED_MODEL --timeout 120
```

Each case invokes Hermes once; its internal tool interactions may require
multiple model requests. A configured provider may charge for those requests.
There is no fixture fallback or automatic outer retry. The command exits 2
when the Hermes executable is missing and 1 if any case fails. Authentication,
provider, and tool failures are reported as failures, not successful checks.

## Acceptance criteria

| Skill | Additional answer check |
|---|---|
| Text2SQL | Execute read-only SQL on non-empty, self-authored SQLite data and compare the returned names as a multiset. Query execution has a SQLite progress limit. |
| Code Author | Execute extra boundary cases not included in the model task's public samples. |
| Bug Hunter | Identify the known empty-list defect at the relevant line and accept the guarded correct example. The English report check is intentionally narrow and may require human interpretation on failure. |
| Code Reviewer | Match the deterministic result computed from the original task. |

The JSON report distinguishes runner status from answer correctness. It records
unique task IDs, the requested model override (or null for the configured
default), and elapsed times. It does not claim to have resolved the effective
provider/model or collected Hermes version metadata; record those from your
local installation when documenting a real run.

The report always leaves `designated_tool_call_proven` false: final result
submission alone cannot prove which terminal commands the model used. Inspect
and sanitize the corresponding Hermes tool traces before making that claim.

Five successful cases demonstrate those smoke cases only. They are not a
general accuracy benchmark or a guarantee that arbitrary tasks will succeed.

## Recorded live verification

On 2026-10-29, the five cases were run against repository commit
`3143086bfcb18d679ea971ce19c19daef945477b` with Hermes v0.16.0
(`2026.6.5`, upstream `c6b0eb4d`), provider `openai-codex`, and model
`gpt-6-luna`. The live cases used the real model; no fixture or mock replaced
live execution.

| Case | Result | Answer check | Elapsed |
|---|---|---|---:|
| Text2SQL | PASS | Executed the read-only query on non-empty controlled data and matched the expected rows. | 12.667 s |
| Code Author | PASS | Executed additional boundary cases omitted from the public task samples. | 12.016 s |
| Bug Hunter, buggy input | PASS | Located and described the known empty-list defect. | 42.046 s |
| Bug Hunter, correct input | PASS | Accepted the guarded implementation with no reported bugs. | 16.612 s |
| Code Reviewer | PASS | Matched the deterministic reviewer result recomputed from the authoritative task. | 10.557 s |

Total per-case elapsed time was 93.898 seconds. The sanitized evidence is
[`artifacts/live-verification-2026-10-29.json`](../artifacts/live-verification-2026-10-29.json),
with SHA-256
`85097cd1a472a39dfe85f71fa6df8d294e8c47147e703ae63a7a0c55c13bbb53`.

The buggy Bug Hunter case needed three candidate submissions within the same
agent execution: the first two failed contract validation and the third passed.
The verifier itself did not retry the case. In the clean Bug Hunter case, the
agent used `printf` to write a simple JSON candidate. That controlled input
succeeded, but it does not establish that `printf` is reliable for arbitrary
quotes, newlines, or shell-special characters.

Every published case keeps `designated_tool_call_proven` false. A human review
of sanitized session traces confirmed terminal calls for all five cases, but
the verifier cannot infer the designated tool call from the final result alone;
the manual observation is not described as automated proof.

These are five controlled smoke tests across four independent skill entry
points. They do not measure overall accuracy, generalization, or production
reliability, and they do not establish an automated generate-review-repair
chain. Keep them distinct from both the reproducible fixture/test-double-based
offline suite and the historical 29/30 result from the former course Text2SQL
submission.

For closeout on the same date, the Python 3.12 offline suite reported 102
passed and 1 integration test deselected. The fixture-based offline demo
validated all four skill examples, and `verify_live.py --dry-run` listed all
five cases with zero model calls.
