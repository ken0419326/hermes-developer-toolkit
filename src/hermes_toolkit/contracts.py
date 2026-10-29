from __future__ import annotations

import math
from typing import Any


SKILLS = {"text2sql", "code-author", "bug-hunter", "code-reviewer"}
BUG_TYPES = {
    "api_misuse", "edge_case", "logic_error", "null_deref",
    "off_by_one", "type_error", "unhandled_input", "unsafe_operation",
}
SEVERITIES = {"critical", "high", "medium", "low", "info"}


class ContractError(ValueError):
    """A result does not satisfy the public output contract."""


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be a JSON object")
    return value


def _string(value: Any, name: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{name} must be a string")
    if nonempty and not value.strip():
        raise ContractError(f"{name} must not be empty")
    return value


def _number(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ContractError(f"{name} must be between {low:g} and {high:g}")
    return result


def task_id_from(task: dict[str, Any]) -> str:
    return _string(task.get("task_id"), "task.task_id")


def _validate_locations(items: Any, field: str, *, max_line: int | None) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise ContractError(f"{field} must be an array")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        item = _object(raw, f"{field}[{index}]")
        start, end = item.get("line_start"), item.get("line_end")
        if isinstance(start, bool) or not isinstance(start, int) or start < 1:
            raise ContractError(f"{field}[{index}].line_start must be a positive integer")
        if isinstance(end, bool) or not isinstance(end, int) or end < start:
            raise ContractError(f"{field}[{index}].line_end must be >= line_start")
        if max_line is not None and end > max_line:
            raise ContractError(f"{field}[{index}] points past the end of the submitted code")
        severity = _string(item.get("severity"), f"{field}[{index}].severity").lower()
        issue_type = _string(item.get("type"), f"{field}[{index}].type").lower()
        if severity not in SEVERITIES:
            raise ContractError(f"{field}[{index}].severity is not supported")
        if issue_type not in BUG_TYPES:
            raise ContractError(f"{field}[{index}].type is not supported")
        normalized_item = dict(item)
        normalized_item.update(
            line_start=start,
            line_end=end,
            severity=severity,
            type=issue_type,
            description=_string(item.get("description"), f"{field}[{index}].description"),
        )
        if "suggested_fix" in item:
            normalized_item["suggested_fix"] = _string(
                item["suggested_fix"], f"{field}[{index}].suggested_fix", nonempty=False
            )
        if "certainty" in item:
            certainty = _string(item["certainty"], f"{field}[{index}].certainty").lower()
            if certainty not in {"high", "medium", "low"}:
                raise ContractError(f"{field}[{index}].certainty is not supported")
            normalized_item["certainty"] = certainty
        normalized.append(normalized_item)
    return normalized


def validate_result(
    skill: str,
    task: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    if skill not in SKILLS:
        raise ContractError(f"unknown skill: {skill}")
    task = _object(task, "task")
    result = _object(result, "result")
    expected_id = task_id_from(task)
    actual_id = _string(result.get("task_id"), "result.task_id")
    if actual_id != expected_id:
        raise ContractError(f"task_id mismatch: expected {expected_id!r}, got {actual_id!r}")

    normalized = dict(result)
    normalized["task_id"] = expected_id
    normalized["confidence"] = _number(result.get("confidence"), "result.confidence", 0.0, 1.0)

    if skill == "text2sql":
        normalized["sql"] = _string(result.get("sql"), "result.sql")
        normalized["rationale"] = _string(result.get("rationale", ""), "result.rationale", nonempty=False)
    elif skill == "code-author":
        normalized["code"] = _string(result.get("code"), "result.code")
        normalized["rationale"] = _string(result.get("rationale", ""), "result.rationale", nonempty=False)
        validation = result.get("validation")
        if validation is not None and not isinstance(validation, dict):
            raise ContractError("result.validation must be an object")
    elif skill == "bug-hunter":
        verdict = _string(result.get("verdict"), "result.verdict").lower()
        if verdict not in {"clean", "buggy"}:
            raise ContractError("result.verdict must be clean or buggy")
        code = task.get("code", "")
        max_line = len(code.splitlines()) if isinstance(code, str) else None
        bugs = _validate_locations(result.get("bugs"), "result.bugs", max_line=max_line)
        if verdict == "clean" and bugs:
            raise ContractError("clean verdict requires an empty bugs array")
        if verdict == "buggy" and not bugs:
            raise ContractError("buggy verdict requires at least one bug")
        normalized.update(verdict=verdict, bugs=bugs)
    else:
        verdict = _string(result.get("verdict"), "result.verdict").lower()
        if verdict not in {"clean", "review_needed"}:
            raise ContractError("result.verdict must be clean or review_needed")
        code = task.get("code", "")
        max_line = len(code.splitlines()) if isinstance(code, str) else None
        findings = _validate_locations(result.get("findings"), "result.findings", max_line=max_line)
        if verdict == "clean" and findings:
            raise ContractError("clean verdict requires an empty findings array")
        if verdict == "review_needed" and not findings:
            raise ContractError("review_needed verdict requires at least one finding")
        normalized.update(verdict=verdict, findings=findings)
    return normalized
