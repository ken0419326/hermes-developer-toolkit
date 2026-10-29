#!/usr/bin/env python3
"""Opt-in, five-case real-Hermes smoke check. No fixture fallback."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import shutil
import sqlite3
import sys
import time
import uuid

from hermes_toolkit.hermes import invoke_hermes
from hermes_toolkit.pipeline import process_candidate
from hermes_toolkit.python_validation import validate_python
from hermes_toolkit.sql_validation import validate_sql


SCHEMA = "CREATE TABLE teams(id INTEGER, name TEXT); CREATE TABLE developers(name TEXT, team_id INTEGER);"
DATA = "INSERT INTO teams VALUES (1,'AI Platform'),(2,'Systems'); INSERT INTO developers VALUES ('Alice',1),('Bob',1),('Carol',2);"


def build_cases(prefix: str) -> list[dict]:
    return [
        {"name": "text2sql", "skill": "text2sql", "task": {
            "task_id": prefix + "-sql", "question": "Return only the names of developers on the AI Platform team, one name column; ordering is not required.",
            "db_schema": SCHEMA, "dialect": "sqlite",
        }},
        {"name": "code-author", "skill": "code-author", "task": {
            "task_id": prefix + "-code", "task_description": "Implement clamp(value, low, high): return low if value < low, high if value > high, otherwise value. Assume low <= high.",
            "constraints": {"entry_function": "clamp", "imports_forbidden": ["os", "subprocess"]},
            "sample_inputs": [{"input": [-2, 0, 10], "expected": 0}, {"input": [4, 0, 10], "expected": 4}],
        }},
        {"name": "bug-hunter-buggy", "skill": "bug-hunter", "task": {
            "task_id": prefix + "-buggy", "task_description": "first_or_none(items) must return None for an empty list, otherwise the first element. Report bugs in English.",
            "code": "def first_or_none(items):\n    return items[0]\n",
        }},
        {"name": "bug-hunter-clean", "skill": "bug-hunter", "task": {
            "task_id": prefix + "-clean", "task_description": "first_or_none(items) must return None for an empty list, otherwise the first element. Report bugs in English.",
            "code": "def first_or_none(items):\n    if not items:\n        return None\n    return items[0]\n",
        }},
        {"name": "code-reviewer", "skill": "code-reviewer", "task": {
            "task_id": prefix + "-review", "task_description": "Review the supplied Python source with the documented static rules.",
            "code": "def run(value):\n    return eval(value)\n",
        }},
    ]


def check_result(case: dict, result: dict) -> tuple[bool, str]:
    """Check controlled examples; these checks are not a general accuracy metric."""
    name, task = case["name"], case["task"]
    if name == "text2sql":
        sql = result.get("sql")
        validation = validate_sql(SCHEMA, sql)
        if not validation.ok:
            return False, validation.error
        with sqlite3.connect(":memory:") as db:
            db.executescript(SCHEMA + DATA)
            db.execute("PRAGMA query_only=ON")
            def authorize(action, *_):
                return sqlite3.SQLITE_OK if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE} else sqlite3.SQLITE_DENY
            db.set_authorizer(authorize)
            # Bound evaluation even if a generated read-only query recurses.
            remaining = [10000]
            def progress():
                remaining[0] -= 1
                return remaining[0] <= 0
            db.set_progress_handler(progress, 1000)
            rows = db.execute(sql).fetchmany(1000)
        correct = Counter(rows) == Counter([("Alice",), ("Bob",)])
        return correct, "matched expected rows" if correct else "query returned incorrect rows or columns"
    if name == "code-author":
        samples = [
            {"input": [12, 0, 10], "expected": 10},
            {"input": [-5, -3, -1], "expected": -3},
            {"input": [-2, -3, -1], "expected": -2},
            {"input": [0, 0, 0], "expected": 0},
        ]
        validation = validate_python(result.get("code"), entry_function="clamp", forbidden_imports=["os", "subprocess"], samples=samples, timeout=2)
        return validation.ok, "passed extra boundary cases" if validation.ok else "failed extra boundary cases"
    if name == "bug-hunter-buggy":
        matches = [b for b in result.get("bugs", []) if b.get("line_start", 0) <= 2 <= b.get("line_end", 0)
                   and b.get("type") in {"edge_case", "unhandled_input", "logic_error"}
                   and any(term in b.get("description", "").lower() for term in ("empty", "indexerror", "out of range"))]
        correct = result.get("verdict") == "buggy" and bool(matches)
        return correct, "identified known empty-list defect" if correct else "did not identify expected defect and location"
    if name == "bug-hunter-clean":
        correct = result.get("verdict") == "clean" and result.get("bugs") == []
        return correct, "accepted correct implementation" if correct else "reported a bug in the controlled correct example"
    expected = process_candidate("code-reviewer", task, None)
    correct = result == expected
    return correct, "matched deterministic reviewer" if correct else "findings differ from deterministic reviewer"


def run_suite(*, invoke=invoke_hermes, model=None, timeout=120.0, label="live") -> dict:
    rows = []
    for case in build_cases("live-" + uuid.uuid4().hex[:12]):
        started = time.monotonic()
        try:
            run = invoke(case["skill"], case["task"], model=model, timeout=timeout)
            ok, detail = check_result(case, run.result) if run.status == "success" and isinstance(run.result, dict) else (False, run.error or run.status)
            rows.append({"case": case["name"], "task_id": case["task"]["task_id"],
                         "status": "PASS" if ok else "FAIL", "runner_status": run.status,
                         "answer_check": detail, "seconds": round(time.monotonic() - started, 3),
                         "designated_tool_call_proven": False})
        except Exception as exc:
            rows.append({"case": case["name"], "status": "FAIL", "error": f"{type(exc).__name__}: {exc}",
                         "designated_tool_call_proven": False})
    return {"mode": label, "requested_model": model, "cases": rows,
            "all_passed": all(r["status"] == "PASS" for r in rows),
            "limits": "Five controlled smoke cases, not a general accuracy benchmark. Tool invocation is not proven without separately inspected Hermes traces."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly enable real model calls using the existing Hermes provider")
    parser.add_argument("--dry-run", action="store_true", help="List cases without calling Hermes")
    parser.add_argument("--model", help="Optional configured Hermes model; otherwise keep the existing default")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps({"mode": "dry-run", "model_calls": 0, "cases": build_cases("preview")}, ensure_ascii=False, indent=2))
        return 0
    if not args.live:
        parser.error("choose --dry-run or explicitly opt in with --live")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if shutil.which("hermes") is None:
        print(json.dumps({"status": "BLOCKED", "reason": "Hermes CLI is not installed", "model_calls": 0}))
        return 2
    report = run_suite(model=args.model, timeout=args.timeout)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
