# Hermes Developer Toolkit

[![Offline tests](https://github.com/ken0419326/hermes-developer-toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/ken0419326/hermes-developer-toolkit/actions/workflows/tests.yml)

Hermes Developer Toolkit is a compact, offline-verifiable set of developer skills for SQL generation, Python function generation, bug reporting, and deterministic static review. It addresses a recurring LLM application problem: a plausible chat response is not a reliable tool result. The toolkit places a typed, mechanically validated, atomic file boundary between a model and downstream automation.

The project is designed for developers experimenting with [Hermes Agent](https://github.com/NousResearch/hermes-agent), and for reviewers who want to inspect or test the deterministic parts without an API key. Hermes supplies the agent runtime, provider integration, skill loading, and terminal tool. This repository supplies the skills, validation pipeline, examples, tests, and documentation.

## What is implemented

| Skill | Input | Output | Mechanically enforced boundary |
|---|---|---|---|
| Text2SQL | Question, SQLite schema | One read-only query | Single statement, read-only policy, SQLite `EXPLAIN` compilation |
| Code Author | Function specification, constraints, samples | Python function | Syntax, entry function, forbidden imports, subprocess sample checks and timeout |
| Bug Hunter | Specification and Python source | Structured bug report | Schema, source ranges, verdict/report consistency |
| Code Reviewer | Python source and optional intent | Deterministic findings | Small documented AST rule set; no model findings accepted |

The Bug Hunter still relies on an LLM for semantic judgment. Its contract validator establishes structure, not bug-report accuracy. The Code Reviewer has a narrower claim: it deterministically implements only the rules in [docs/STATIC_RULES.md](docs/STATIC_RULES.md).

## Architecture and data flow

```text
original task JSON ─────────────────────────────┐
                                               │ binds task_id
model candidate JSON (stdin or file) ──> shared pipeline
                                               ├─> typed contract checks
                                               ├─> SQL or Python validation
                                               └─> atomic result.json

Hermes (optional) ──> skill prompt ──> terminal wrapper ──> shared pipeline
offline demo       ──> fixture candidate ────────────────> shared pipeline
```

The candidate normally omits `task_id`; the pipeline obtains it from the original task. If a model restates a different ID, processing fails. SQL and Python are carried inside JSON through stdin or files rather than interpolated into shell arguments.

## Quickstart: no API key required

Requirements: Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python examples/offline_demo.py
pytest -m 'not integration'
```

If the machine is intentionally offline and already has compatible setuptools and pytest installations, use `python -m pip install -e '.[dev]' --no-build-isolation` to prevent pip from creating a network-fetched build environment.

The demo labels all model candidates as **fixtures**. It calls no model and makes no model-quality claim. It demonstrates task ingestion, candidate processing, deterministic validation, and atomic output for all four skills.

## Input and output examples

### Text2SQL

Task:

```json
{
  "task_id": "sql-001",
  "question": "List developers on the AI Platform team.",
  "db_schema": "CREATE TABLE teams(id INTEGER, name TEXT); CREATE TABLE developers(name TEXT, team_id INTEGER);",
  "dialect": "sqlite"
}
```

Candidate supplied by a model or fixture:

```json
{
  "sql": "SELECT d.name FROM developers d JOIN teams t ON d.team_id=t.id WHERE t.name='AI Platform'",
  "rationale": "Join developers to their team and filter by name.",
  "confidence": 0.9
}
```

The written result adds the original `task_id` and a deterministic `validation` object.

### Code Author

The task declares `constraints.entry_function`, forbidden imports, and sample input/expected-output pairs. The candidate contains `code`, `rationale`, and `confidence`. The result is written only if the source parses, defines the entry function, avoids forbidden imports, and passes every supplied sample.

### Bug Hunter

The candidate contains `verdict`, `bugs`, and `confidence`. Every bug has a source range, severity, type, description, and optional fix. Clean reports must have no bugs; buggy reports must contain at least one in-range bug.

### Code Reviewer

The reviewer takes source directly from the original task and produces `clean` or `review_needed`. For example, direct `eval()` is a high-certainty `unsafe_operation`; unguarded `items[0]` is a medium-certainty edge-case finding. It does not claim whole-program correctness.

Complete runnable examples are under [`examples/`](examples/).

## Output and error handling

The central contract rejects missing files, invalid JSON, non-object roots, missing fields, incorrect types, non-finite confidence, task-ID mismatches, invalid source ranges, SQL compilation failures, Python validation failures, tool failures, and timeouts.

Only a fully validated result is written. The writer creates a temporary file in the destination directory, flushes and `fsync`s it, then replaces the destination atomically. Details are in [docs/CONTRACTS.md](docs/CONTRACTS.md).

Candidate Python samples run in separate subprocesses with bounded timeouts. This limits hangs and keeps candidate globals out of the validator process; it is **not a secure sandbox for hostile code**. Do not run untrusted code without OS-level isolation.

## Offline tests versus real-model tests

```bash
# Reproducible and API-key free; used by CI
pytest -m 'not integration'

# Optional: requires a working Hermes CLI and a real configured provider
HERMES_INTEGRATION=1 pytest -m integration
```

The offline suite covers successful results, contract failures, Unicode, quotes and newlines, atomic writes, SQL checks, Python entry/import/sample checks, subprocess timeout, reviewer positive and negative cases, and mocked Hermes success/error/timeout boundaries.

Integration tests do not silently fall back to mocks. Without `HERMES_INTEGRATION=1` and a configured Hermes installation, they are reported as skipped. The former course gateway is no longer available, so this portfolio edition has not been evaluated with a live LLM.

## Configuring a provider or model

Copy and edit [`examples/hermes-config.example.yaml`](examples/hermes-config.example.yaml) in your local Hermes configuration directory:

1. Set an OpenAI-compatible endpoint you are authorized to use.
2. Set its credential environment-variable name; keep the actual value out of Git.
3. Set the provider's model identifier and suitable context/output limits.
4. Point `skills.external_dirs` to this repository's `skills` directory.
5. Run the integration test explicitly.

No endpoint or model is required for offline validation. No live endpoint/model combination has been verified for this refactored edition.

## Test and CI commands

```bash
python examples/offline_demo.py
pytest -m 'not integration'
pytest tests/test_reviewer.py -q
```

GitHub Actions installs the package on Python 3.10 and 3.12, runs the offline demo, and executes the offline suite. It does not use provider credentials.

## Limitations and next work

- Deterministic validation can reject malformed outputs but cannot prove LLM semantic accuracy.
- Python subprocess execution is not a hostile-code sandbox.
- The static reviewer intentionally implements a small rule set and may miss defects outside it.
- The range-boundary rule needs explicit all-items intent; it does not flag adjacent-pair algorithms.
- Real Hermes/model behavior, retry quality, latency, and token cost remain unmeasured for this edition.
- A future evaluation should use a redistributable labeled dataset and report precision/recall separately from determinism.

## Provenance and historical result

This is a standalone portfolio refactor of Ken Shen's university final project. The original project was built on Hermes Agent and a course starter repository. Course gold answers, grader code, reference opponents, private feedback, and gateway-specific credentials/configuration are not included.

The original course Text2SQL submission received **29/30** on its Basic Track assessment. This historical number applies only to the course version; the original execution artifacts are unavailable, and it is not attributed to this refactor. See [docs/HISTORICAL_ASSESSMENT.md](docs/HISTORICAL_ASSESSMENT.md).

See [docs/PROVENANCE.md](docs/PROVENANCE.md) for the division between Hermes/upstream capabilities and the portfolio implementation, and [CHANGES.md](CHANGES.md) for the refactor record.

## License

The portfolio code in this repository is MIT licensed. Hermes Agent is a separate upstream project governed by its own license and terms.
