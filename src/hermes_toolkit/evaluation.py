"""Repeatable, opt-in Hermes evaluation with checkpointing and explicit limits."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import shutil
import sqlite3
import statistics
import subprocess
import time
import uuid

from .contracts import validate_result
from .evaluation_cases import build_cases
from .hermes import invoke_hermes
from .io import atomic_write_json, load_json_object
from .pipeline import process_candidate
from .python_validation import validate_python
from .sql_validation import validate_sql

FORMAT = 1


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _sql_rows(schema: str, data: str, query: str) -> list:
    check = validate_sql(schema, query)
    if not check.ok:
        raise ValueError("SQL validation failed")
    with sqlite3.connect(":memory:") as db:
        db.executescript(schema + data)
        db.execute("PRAGMA query_only=ON")
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
        db.set_authorizer(lambda action, *_: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
        budget = [1000]
        def progress():
            budget[0] -= 1
            return budget[0] <= 0
        db.set_progress_handler(progress, 1000)
        rows = db.execute(query).fetchmany(1001)
        if len(rows) > 1000:
            raise ValueError("SQL output exceeds evaluation row bound")
        return rows


def grade(case: dict, task: dict, result: dict, *, sample_timeout=2.0) -> dict:
    """Only task is sent to Hermes; case.oracle stays with the evaluator."""
    skill, oracle = case["skill"], case["oracle"]
    # Revalidate independently of HermesRun.status or a model's validation flag.
    result = process_candidate(skill, task, result, sample_timeout=sample_timeout) if skill != "code-reviewer" else validate_result(skill, task, result)
    if oracle["kind"] == "sql":
        matches = []
        for data in oracle["datasets"]:
            expected = _sql_rows(task["db_schema"], data, oracle["query"])
            actual = _sql_rows(task["db_schema"], data, result["sql"])
            matches.append(Counter(actual) == Counter(expected))
        return {"passed": all(matches), "detail": "SQL result bags across independent data fixtures", "checks": matches}
    if oracle["kind"] == "python":
        entry = task["constraints"]["entry_function"]
        # Verify input non-mutation as well as returned values on the private samples.
        wrapper = "_evaluation_" + uuid.uuid4().hex
        source = result["code"] + (
            f"\n\ndef {wrapper}(*args, **kwargs):\n"
            "    import copy\n"
            "    before = copy.deepcopy((args, kwargs))\n"
            f"    value = {entry}(*args, **kwargs)\n"
            "    if (args, kwargs) != before:\n"
            "        raise AssertionError('input mutation')\n"
            "    return value\n"
        )
        validation = validate_python(source, entry_function=wrapper, forbidden_imports=task["constraints"]["imports_forbidden"], samples=oracle["samples"], timeout=sample_timeout)
        return {"passed": validation.ok, "detail": "extra functional and input-mutation checks", "checks": [s.passed for s in validation.samples]}
    if oracle["kind"] == "bug":
        predicted = result["verdict"] == "buggy"
        bugs = result["bugs"]
        matched = sum(
            b["line_start"] <= oracle["line"] <= b["line_end"]
            and b["line_end"] - b["line_start"] <= 1
            and b["type"] in oracle["types"]
            and any(term in b["description"].lower() for term in oracle["terms"])
            for b in bugs
        ) if oracle["buggy"] else 0
        # One known defect per positive task: extra or duplicate reports fail strict grading.
        passed = (predicted and matched == 1 and len(bugs) == 1) if oracle["buggy"] else not predicted
        return {"passed": passed, "detail": "controlled defect location/type/English-keyword oracle", "expected_buggy": oracle["buggy"], "predicted_buggy": predicted}
    actual = [[f.get("rule_id"), f["line_start"], f["line_end"], f["type"]] for f in result["findings"]]
    expected = oracle["findings"]
    a, e = Counter(map(tuple, actual)), Counter(map(tuple, expected))
    return {"passed": a == e and result["verdict"] == ("review_needed" if expected else "clean"),
            "detail": "independently specified static-rule gold findings", "finding_tp": sum((a & e).values()),
            "finding_fp": sum((a - e).values()), "finding_fn": sum((e - a).values())}


def make_plan(cases: list[dict], repeats: int, seed: int) -> list[dict]:
    if repeats < 1 or not cases or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("need positive repeats and unique, nonempty cases")
    rng = random.Random(seed)
    plan = []
    # Round-wise shuffling spreads repeated tasks over time.
    for repeat in range(1, repeats + 1):
        order = list(cases)
        rng.shuffle(order)
        plan.extend({"case_id": c["id"], "skill": c["skill"], "repeat": repeat} for c in order)
    return plan


def _latencies(rows: list[dict]) -> dict:
    values = sorted(r["seconds"] for r in rows if isinstance(r.get("seconds"), (int, float)))
    if not values:
        return {"n": 0, "median_seconds": None, "p95_seconds": None}
    position = (len(values) - 1) * .95
    lower, upper = math.floor(position), math.ceil(position)
    p95 = values[lower] + (values[upper] - values[lower]) * (position - lower)
    return {"n": len(values), "median_seconds": round(statistics.median(values), 3), "p95_seconds": round(p95, 3)}


def summarize(manifest: dict, rows: list[dict]) -> dict:
    def group(plan, recorded):
        n, passed = len(recorded), sum(r["passed"] for r in recorded)
        ids = {p["case_id"] for p in plan}
        completed_tasks = [i for i in ids if sum(r["case_id"] == i for r in recorded) == manifest["repeats"]]
        stable = sum(all(r["passed"] for r in recorded if r["case_id"] == i) for i in completed_tasks)
        return {"planned": len(plan), "recorded": n, "passed": passed, "failed": n - passed,
                "unrun": len(plan) - n, "success_rate_among_recorded": passed / n if n else None,
                "completed_repeated_tasks": len(completed_tasks), "tasks_passing_all_repeats": stable,
                "all_repeats_success_rate": stable / len(completed_tasks) if completed_tasks else None,
                "failure_categories": dict(Counter(r["failure_category"] for r in recorded if not r["passed"])),
                "latency_all_recorded": _latencies(recorded), "latency_successful": _latencies([r for r in recorded if r["passed"]])}
    report = {"mode": manifest["mode"], "manifest_sha256": digest(manifest), "complete": len(rows) == len(manifest["plan"]),
              "overall": group(manifest["plan"], rows), "by_skill": {}}
    for skill in sorted({p["skill"] for p in manifest["plan"]}):
        report["by_skill"][skill] = group([p for p in manifest["plan"] if p["skill"] == skill], [r for r in rows if r["skill"] == skill])
    bug_rows = [r for r in rows if r["skill"] == "bug-hunter"]
    usable = [r["grade"] for r in bug_rows if "predicted_buggy" in r.get("grade", {})]
    tp = sum(g["predicted_buggy"] and g["expected_buggy"] for g in usable)
    fp = sum(g["predicted_buggy"] and not g["expected_buggy"] for g in usable)
    fn = sum(not g["predicted_buggy"] and g["expected_buggy"] for g in usable)
    tn = sum(not g["predicted_buggy"] and not g["expected_buggy"] for g in usable)
    report["bug_verdict_metrics"] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "ungraded_runs": len(bug_rows)-len(usable),
        "precision": tp/(tp+fp) if tp+fp else None, "recall": tp/(tp+fn) if tp+fn else None,
        "specificity": tn/(tn+fp) if tn+fp else None,
        "limits": "Binary verdicts on graded runs only; strict defect checks remain in task success. Ungraded runs are not counted as clean."}
    report["unmeasured"] = {"first_candidate_success_rate": None, "candidate_submission_count": None,
                            "actual_provider_and_model": None, "token_cost": None, "designated_tool_call_proven": False}
    report["limits"] = ["Public synthetic regression suite, not a sealed held-out benchmark.",
        "Repeated runs of the same tasks are correlated; report distinct task counts.",
        "Latency includes agent execution plus local grading and is not model-only latency.",
        "No verifier retries; an agent can correct candidates within one invocation.",
        "No safe-code sandbox: execute only controlled tasks in a disposable, least-privilege environment."]
    return report


def run_evaluation(cases: list[dict], manifest: dict, *, output: Path, invoke=invoke_hermes,
                   resume=False, max_invocations=120, max_wall_seconds=3600.0, stop_after_failures=3) -> dict:
    """Checkpoint each started invocation; resume never silently retries recorded failures."""
    if max_invocations < 1 or max_wall_seconds <= 0 or stop_after_failures < 1:
        raise ValueError("execution limits must be positive")
    if manifest.get("suite_sha256") != digest(cases):
        raise ValueError("case bank differs from manifest")
    if resume:
        state = load_json_object(output)
        if state.get("manifest") != manifest or state.get("manifest_sha256") != digest(manifest):
            raise ValueError("resume manifest differs: refuse to mix evaluations")
        rows = state["rows"]
        prefix = manifest["plan"][:len(rows)]
        if len(rows) > len(manifest["plan"]) or any(
            {k: row.get(k) for k in ("case_id", "skill", "repeat")} != planned
            for row, planned in zip(rows, prefix)
        ):
            raise ValueError("checkpoint rows are not a unique plan prefix")
    else:
        if output.exists():
            raise ValueError("output already exists; use --resume or a new output path")
        rows = []
    state = {"format": FORMAT, "manifest": manifest, "manifest_sha256": digest(manifest), "rows": rows}
    index = {c["id"]: c for c in cases}
    started, invoked, failures = time.monotonic(), 0, 0
    stop = "complete"
    for planned in manifest["plan"][len(rows):]:
        if manifest.get("source") and _source_identity() != manifest["source"]:
            stop = "source_changed"
            break
        if invoked >= max_invocations or time.monotonic()-started >= max_wall_seconds:
            stop = "execution_budget_reached"
            break
        case = index[planned["case_id"]]
        task = deepcopy(case["task"])
        task["task_id"] = manifest["run_id"] + "-" + case["id"] + "-" + str(planned["repeat"])
        row = dict(planned, task_id=task["task_id"], passed=False, runner_status="interrupted",
                   failure_category="interrupted", seconds=None, grade={}, final_result=None,
                   designated_tool_call_proven=False)
        rows.append(row)
        # If killed during the call, this interrupted attempt remains a recorded failure.
        atomic_write_json(output, state)
        call_started = time.monotonic()
        try:
            run = invoke(case["skill"], task, model=manifest["requested_model"], timeout=manifest["timeout_seconds"])
            row["runner_status"] = run.status
            if run.status != "success" or not isinstance(run.result, dict):
                row["failure_category"] = run.status if run.status in {"timeout", "tool_error", "invalid_result"} else "runner_error"
            else:
                row["final_result"] = run.result
                try:
                    row["grade"] = grade(case, task, run.result, sample_timeout=manifest["sample_timeout_seconds"])
                    row["passed"] = row["grade"]["passed"]
                    row["failure_category"] = None if row["passed"] else "answer_mismatch"
                except Exception as exc:
                    row.update(failure_category="grading_error", grading_exception=type(exc).__name__)
        except Exception as exc:
            # Do not persist CLI stdout/stderr or arbitrary exception text (may contain secrets).
            row.update(runner_status="exception", failure_category="invocation_exception", invocation_exception=type(exc).__name__)
        finally:
            row["seconds"] = round(time.monotonic()-call_started, 3)
            atomic_write_json(output, state)
        if manifest.get("source") and _source_identity() != manifest["source"]:
            row.update(passed=False, failure_category="source_changed")
            atomic_write_json(output, state)
            stop = "source_changed"
            break
        invoked += 1
        failures = 0 if row["passed"] else failures+1
        if failures >= stop_after_failures and len(rows) < len(manifest["plan"]):
            stop = "consecutive_failure_limit"
            break
    report = summarize(manifest, rows)
    report["stop_reason"] = stop
    atomic_write_json(output.with_name(output.stem + "-summary.json"), report)
    return report


@contextmanager
def output_lock(output: Path):
    lock = output.with_name(output.name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        yield
    finally:
        lock.unlink()


def _source_identity() -> dict:
    root = Path(__file__).resolve().parents[2]
    paths = sorted(list(Path(__file__).parent.glob("*.py")) + list((root/"skills").glob("*/SKILL.md")) + list((root/"skills").glob("*/scripts/*.py")))
    sources = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    commit = None
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, timeout=5, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True, capture_output=True, timeout=5, check=True).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        dirty = None
    return {"commit": commit, "tracked_worktree_dirty": dirty, "source_sha256": digest(sources)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--provider-label", default="unspecified", help="User-supplied label, not a provider switch or attestation")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skill", action="append", choices=["text2sql","code-author","bug-hunter","code-reviewer"])
    parser.add_argument("--limit-per-skill", type=int)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--sample-timeout", type=float, default=2.0)
    parser.add_argument("--output", type=Path, default=Path("outputs/evaluation/run.json"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-invocations", type=int, default=120, help="Maximum new agent invocations in this launch, not API request count")
    parser.add_argument("--max-wall-seconds", type=float, default=3600.0, help="Stop starting tasks after this budget; an active task may finish later")
    parser.add_argument("--stop-after-failures", type=int, default=3)
    args = parser.parse_args(argv)
    positive = [args.repeats, args.timeout, args.sample_timeout, args.max_invocations, args.max_wall_seconds, args.stop_after_failures]
    if any(v <= 0 or not math.isfinite(v) for v in positive) or (args.limit_per_skill is not None and args.limit_per_skill < 1):
        parser.error("counts and timeouts must be positive and finite")
    cases = build_cases()
    if args.skill:
        cases = [c for c in cases if c["skill"] in args.skill]
    if args.limit_per_skill:
        counts = Counter()
        selected = []
        for c in cases:
            if counts[c["skill"]] < args.limit_per_skill:
                selected.append(c)
                counts[c["skill"]] += 1
        cases = selected
    plan = make_plan(cases, args.repeats, args.seed)
    base = {"format": FORMAT, "mode": "live", "suite_sha256": digest(cases), "source": _source_identity(),
            "runtime": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "system": platform.system()},
            "requested_model": args.model, "provider_label_unverified": args.provider_label,
            "repeats": args.repeats, "seed": args.seed, "timeout_seconds": args.timeout,
            "sample_timeout_seconds": args.sample_timeout, "plan": plan}
    if args.dry_run:
        print(json.dumps({"mode": "dry-run", "agent_invocations": 0, "distinct_tasks": len(cases),
            "planned_agent_invocations": len(plan), "by_skill": dict(Counter(c["skill"] for c in cases)),
            "timeout_upper_bound_seconds_excluding_grading": len(plan)*args.timeout,
            "suite_sha256": base["suite_sha256"], "plan_sha256": digest(plan),
            "limits": "Each agent invocation can make multiple model/tool calls. Repeats measure repeatability, not deterministic model output."}, indent=2))
        return 0
    if not args.model:
        parser.error("--live requires an explicit --model")
    if base["source"]["commit"] is None or base["source"]["tracked_worktree_dirty"] is not False:
        print(json.dumps({"status": "BLOCKED", "reason": "Commit changes and use a clean Git checkout before a live evaluation", "agent_invocations": 0}))
        return 2
    if shutil.which("hermes") is None:
        print(json.dumps({"status": "BLOCKED", "reason": "Hermes CLI is not installed", "agent_invocations": 0}))
        return 2
    try:
        version = subprocess.run(["hermes", "--version"], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        if args.resume:
            old = load_json_object(args.output)["manifest"]
            manifest = dict(base, run_id=old["run_id"], started_at_utc=old["started_at_utc"], hermes_version=version)
        else:
            manifest = dict(base, run_id="eval-"+uuid.uuid4().hex[:12], started_at_utc=datetime.now(timezone.utc).isoformat(), hermes_version=version)
        with output_lock(args.output):
            report = run_evaluation(cases, manifest, output=args.output, resume=args.resume,
                max_invocations=args.max_invocations, max_wall_seconds=args.max_wall_seconds, stop_after_failures=args.stop_after_failures)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason_type": type(exc).__name__, "reason": "Check output path/lock, resume manifest, and Hermes version; no credentials are inspected."}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["complete"] and report["overall"]["failed"] == 0 else 1
