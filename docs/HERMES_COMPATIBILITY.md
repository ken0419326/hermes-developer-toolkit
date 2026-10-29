# Hermes CLI and skill compatibility

This document records both interface checks and one narrowly scoped live-model
compatibility observation. It is not a general model evaluation.

## Locally inspected version

On 2026-10-29, development inspected:

```text
Hermes Agent v0.16.0 (2026.6.5), upstream c6b0eb4d
```

`hermes chat --help` in that installation exposes the flags used by the runner:

- `-q` / `--query`
- `-m` / `--model`
- `-t` / `--toolsets`
- `-s` / `--skills`
- `-Q` / `--quiet`
- `--yolo`

The installed skill preprocessor also contains `${HERMES_SKILL_DIR}` substitution, enabled by the default `skills.template_vars` setting. Current upstream [skill authoring documentation](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/creating-skills.md) and [CLI reference](https://github.com/hermes-agent-org/hermes/blob/main/website/docs/reference/cli-commands.md), inspected on the same date, describe the same skill-directory token, `skills.external_dirs`, and CLI flags. Exact behavior can change in later releases; check `hermes --version` and `hermes chat --help` locally.

## Task handoff

`invoke_hermes()` writes the authoritative task to a temporary UTF-8 JSON file and exports:

- `HERMES_TOOLKIT_TASK_PATH`
- `HERMES_TOOLKIT_CANDIDATE_PATH`
- `HERMES_TOOLKIT_OUTPUT_PATH`

It preloads the requested skill with `-s` and sends a query that includes the exact task path and requires the skill to read it before reasoning. Each SKILL.md repeats that requirement and invokes its wrapper through the absolute `${HERMES_SKILL_DIR}` path. Candidate-producing skills write JSON to the candidate path using a quoted literal heredoc, then pass the file with `--candidate`.

Offline boundary tests verify argv construction, environment handoff, paths containing spaces/quotes/Unicode, wrapper execution from unrelated working directories, and result finalization.

## Live compatibility observation

On 2026-10-29, repository commit
`3143086bfcb18d679ea971ce19c19daef945477b` completed all five controlled
smoke cases with Hermes v0.16.0, provider `openai-codex`, and model
`gpt-6-luna`. This used real model execution, not fixtures or mocks. The checks
and elapsed times are recorded in [LIVE_SMOKE.md](LIVE_SMOKE.md).

Manual review of sanitized traces confirmed terminal calls. The verifier still
records `designated_tool_call_proven: false`, because a successful final result
does not itself prove which tool produced it. This manual trace observation is
not automated attestation.

The following remain unverified:

- task-file and terminal behavior in other Hermes backends, container modes, releases, providers, or models;
- arbitrary quoting, newline, and shell-special-character reliability when a model chooses `printf` rather than the documented file-safe pattern;
- provider-specific retry quality, token cost, and broad latency behavior;
- accuracy, generalization, or production reliability beyond the five controlled cases;
- orchestration of the four independent skills into an automated generate-review-repair chain.

Mocked subprocess tests remain offline results and are not reported as live
Hermes integration. The original course Text2SQL 29/30 result is historical and
does not apply to this compatibility run.
