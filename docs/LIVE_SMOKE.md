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

## Current verification state

The verifier has offline tests for its answer checks and success/failure paths.
Real model results remain unverified until an actual `--live` run is recorded.
Do not attribute the original course's 29/30 assessment to this verifier.
