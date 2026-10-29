from __future__ import annotations

import ast
import re
from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class Finding:
    line_start: int
    line_end: int
    severity: str
    type: str
    description: str
    suggested_fix: str
    certainty: str
    rule_id: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _guarded_names(statements: Iterable[ast.stmt]) -> set[str]:
    guarded: set[str] = set()
    for statement in statements:
        if not isinstance(statement, ast.If):
            continue
        test = statement.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) and isinstance(test.operand, ast.Name):
            guarded.add(test.operand.id)
        if isinstance(test, ast.Compare) and isinstance(test.left, ast.Call) and _name(test.left.func) == "len":
            if test.left.args and isinstance(test.left.args[0], ast.Name):
                guarded.add(test.left.args[0].id)
    return guarded


class StaticReviewer(ast.NodeVisitor):
    def __init__(self, task_description: str = "") -> None:
        self.task_description = task_description.lower()
        self.findings: list[Finding] = []
        self._function_guards: list[set[str]] = []

    def _add(self, node: ast.AST, **fields: str) -> None:
        self.findings.append(Finding(
            line_start=getattr(node, "lineno", 1),
            line_end=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            **fields,
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_guards.append(_guarded_names(node.body))
        self.generic_visit(node)
        self._function_guards.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        called = _name(node.func)
        if called in {"eval", "exec", "os.system"}:
            self._add(
                node,
                severity="high",
                type="unsafe_operation",
                description=f"{called} executes dynamically supplied code or commands.",
                suggested_fix="Use a structured API and validate inputs instead of dynamic execution.",
                certainty="high",
                rule_id="unsafe-dynamic-execution",
            )
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        container = _name(node.value)
        constant_zero = isinstance(node.slice, ast.Constant) and node.slice.value in {0, -1}
        guards = self._function_guards[-1] if self._function_guards else set()
        if container and constant_zero and container not in guards:
            self._add(
                node,
                severity="medium",
                type="edge_case",
                description=f"Indexing {container} without a visible empty-input guard may raise IndexError.",
                suggested_fix="Guard empty input or document and validate a non-empty precondition.",
                certainty="medium",
                rule_id="unguarded-constant-index",
            )
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        # range(len(x) - 1) can be correct for adjacent-pair algorithms. Flag it
        # only when the task explicitly says every/all elements must be handled.
        iterator = node.iter
        process_all = bool(re.search(r"\b(all|every)\s+(element|item|number|value)s?\b", self.task_description))
        if process_all and isinstance(iterator, ast.Call) and _name(iterator.func) == "range" and len(iterator.args) == 1:
            arg = iterator.args[0]
            if (
                isinstance(arg, ast.BinOp)
                and isinstance(arg.op, ast.Sub)
                and isinstance(arg.right, ast.Constant)
                and arg.right.value == 1
                and isinstance(arg.left, ast.Call)
                and _name(arg.left.func) == "len"
            ):
                self._add(
                    node,
                    severity="medium",
                    type="off_by_one",
                    description="The loop excludes the final item although the task says all items must be processed.",
                    suggested_fix="Use range(len(values)) or iterate over the values directly.",
                    certainty="medium",
                    rule_id="all-items-range-minus-one",
                )
        self.generic_visit(node)


def review_code(code: str, task_description: str = "") -> dict[str, object]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        line = exc.lineno or 1
        finding = Finding(
            line, line, "high", "logic_error", f"Python syntax error: {exc.msg}",
            "Correct the syntax before review.", "high", "python-syntax-error",
        )
        findings = [finding]
    else:
        reviewer = StaticReviewer(task_description)
        reviewer.visit(tree)
        findings = sorted(reviewer.findings, key=lambda item: (item.line_start, item.rule_id))
    return {
        "verdict": "review_needed" if findings else "clean",
        "findings": [item.to_dict() for item in findings],
    }
