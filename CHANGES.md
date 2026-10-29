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
