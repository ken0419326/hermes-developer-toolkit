from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import ContractError, task_id_from, validate_result
from .io import atomic_write_json
from .python_validation import validate_python
from .reviewer import review_code
from .sql_validation import validate_sql


class PipelineError(RuntimeError):
    """A candidate failed deterministic processing or validation."""


def _candidate_with_task_id(task: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    expected = task_id_from(task)
    supplied = candidate.get("task_id")
    if supplied is not None and supplied != expected:
        raise PipelineError(f"candidate task_id mismatch: expected {expected!r}, got {supplied!r}")
    result = dict(candidate)
    result["task_id"] = expected
    return result


def process_candidate(
    skill: str,
    task: dict[str, Any],
    candidate: dict[str, Any] | None,
    *,
    output_path: str | Path | None = None,
    sample_timeout: float = 2.0,
) -> dict[str, Any]:
    try:
        task_id_from(task)
        if skill == "code-reviewer":
            code = task.get("code")
            if not isinstance(code, str) or not code.strip():
                raise PipelineError("task.code must be a non-empty string")
            generated = review_code(code, str(task.get("task_description", "")))
            generated.update(task_id=task["task_id"], confidence=1.0)
            result = generated
        else:
            if not isinstance(candidate, dict):
                raise PipelineError("candidate must be a JSON object")
            result = _candidate_with_task_id(task, candidate)

        if skill == "text2sql":
            validation = validate_sql(str(task.get("db_schema", "")), result.get("sql"))
            if not validation.ok:
                raise PipelineError(validation.error)
            result["validation"] = validation.to_dict()
        elif skill == "code-author":
            constraints = task.get("constraints") or {}
            if not isinstance(constraints, dict):
                raise PipelineError("task.constraints must be an object")
            entry = constraints.get("entry_function")
            if not isinstance(entry, str) or not entry:
                raise PipelineError("task.constraints.entry_function must be a non-empty string")
            samples = task.get("sample_inputs", [])
            if not isinstance(samples, list):
                raise PipelineError("task.sample_inputs must be an array")
            validation = validate_python(
                result.get("code"),
                entry_function=entry,
                forbidden_imports=constraints.get("imports_forbidden", []),
                samples=samples,
                timeout=sample_timeout,
            )
            result["validation"] = validation.to_dict()
            if not validation.ok:
                raise PipelineError("candidate Python failed deterministic validation")
        normalized = validate_result(skill, task, result)
    except ContractError as exc:
        raise PipelineError(str(exc)) from exc
    if output_path is not None:
        atomic_write_json(output_path, normalized)
    return normalized
