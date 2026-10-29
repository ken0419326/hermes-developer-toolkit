# Hermes CLI and skill compatibility

This document records interface checks, not a live-model evaluation.

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

## Not verified

No provider or model was called during this hardening work. The following remain unverified:

- whether a particular live model follows the task-file instruction;
- terminal-tool environment propagation in every Hermes backend/container mode;
- provider-specific tool-calling, retry, latency, and token behavior;
- Hermes releases other than the locally inspected v0.16.0 interface.

Mocked subprocess tests are not reported as live Hermes integration results.
