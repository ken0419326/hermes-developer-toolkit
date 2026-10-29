from __future__ import annotations

import ast
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class SampleResult:
    index: int
    passed: bool
    error: str = ""


@dataclass(frozen=True)
class PythonValidation:
    ok: bool
    syntax_error: str
    entry_found: bool
    import_violations: tuple[str, ...]
    samples: tuple[SampleResult, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["import_violations"] = list(self.import_violations)
        value["samples"] = [asdict(item) for item in self.samples]
        return value


def _imports(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def _run_sample(code: str, entry: str, sample: dict[str, Any], index: int, timeout: float) -> SampleResult:
    payload = {
        "code": code,
        "entry_function": entry,
        "args": sample.get("input", sample.get("args", [])),
        "kwargs": sample.get("kwargs", {}),
    }
    try:
        process = subprocess.run(
            [sys.executable, "-m", "hermes_toolkit._sample_worker"],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SampleResult(index, False, f"sample timed out after {timeout:g}s")
    try:
        response = json.loads(process.stdout)
    except json.JSONDecodeError:
        detail = process.stderr.strip() or process.stdout.strip() or f"worker exited {process.returncode}"
        return SampleResult(index, False, f"sample worker produced invalid output: {detail}")
    if not response.get("ok"):
        return SampleResult(index, False, f"{response.get('error_type', 'Error')}: {response.get('error', '')}")
    if "expected" in sample and response.get("value") != sample["expected"]:
        return SampleResult(
            index,
            False,
            f"expected {sample['expected']!r}, got {response.get('value')!r}",
        )
    return SampleResult(index, True)


def validate_python(
    code: str,
    *,
    entry_function: str,
    forbidden_imports: list[str] | tuple[str, ...] = (),
    samples: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    timeout: float = 2.0,
) -> PythonValidation:
    if not isinstance(code, str) or not code.strip():
        return PythonValidation(False, "code must be a non-empty string", False, (), ())
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        message = f"line {exc.lineno}: {exc.msg}"
        return PythonValidation(False, message, False, (), ())
    entry_found = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == entry_function
        for node in tree.body
    )
    forbidden = {name.split(".")[0] for name in forbidden_imports}
    violations = tuple(sorted(_imports(tree) & forbidden))
    if not entry_found or violations:
        return PythonValidation(False, "", entry_found, violations, ())
    results = tuple(
        _run_sample(code, entry_function, sample, index, timeout)
        for index, sample in enumerate(samples)
    )
    return PythonValidation(all(item.passed for item in results), "", True, violations, results)
