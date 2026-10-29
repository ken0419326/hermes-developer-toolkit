from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from hermes_toolkit import evaluation as ev
from hermes_toolkit.evaluation_cases import build_cases
from hermes_toolkit.hermes import HermesRun
from hermes_toolkit.pipeline import process_candidate


def task_for(case):
    return dict(deepcopy(case["task"]), task_id="offline-"+case["id"])


def reference(case, task):
    oracle = case["oracle"]
    candidate = {"confidence": .8}
    if oracle["kind"] == "sql":
        candidate["sql"] = oracle["query"]
    elif oracle["kind"] == "python":
        candidate["code"] = oracle["reference"]
    elif oracle["kind"] == "bug":
        candidate.update(verdict="buggy" if oracle["buggy"] else "clean", bugs=[])
        if oracle["buggy"]:
            candidate["bugs"] = [{"line_start": oracle["line"], "line_end": oracle["line"],
                "type": oracle["types"][0], "severity": "medium", "description": oracle["terms"][0]}]
    return process_candidate(case["skill"], task, candidate)


def manifest(cases, repeats=3):
    return {"mode": "offline-harness-test", "run_id": "offline-test", "suite_sha256": ev.digest(cases),
            "repeats": repeats, "plan": ev.make_plan(cases, repeats, 42),
            "requested_model": "test-double", "timeout_seconds": 1, "sample_timeout_seconds": 1}


def test_bank_structure_and_gold_is_not_in_task():
    cases = build_cases()
    assert len(cases) == len({c["id"] for c in cases}) == 40
    assert set(Counter(c["skill"] for c in cases).values()) == {10}
    assert sum(c["oracle"].get("buggy", False) for c in cases) == 5
    for c in cases:
        assert "oracle" not in c["task"] and "task_id" not in c["task"]
        if c["skill"] == "text2sql":
            assert len(c["oracle"]["datasets"]) == 3
        if c["skill"] == "code-author":
            assert len(c["oracle"]["samples"]) >= 5


@pytest.mark.parametrize("case", build_cases(), ids=lambda c: c["id"])
def test_independent_gold_and_reference_cases(case):
    task = task_for(case)
    assert ev.grade(case, task, reference(case, task))["passed"]


def test_sql_rejects_query_that_only_fits_first_database():
    case = build_cases()[0]
    task = task_for(case)
    result = process_candidate("text2sql", task, {"confidence":1, "sql":"SELECT 'Ada' UNION ALL SELECT 'Dee'"})
    graded = ev.grade(case, task, result)
    assert graded["checks"][0] and not graded["passed"]


def test_sql_bag_comparison_preserves_duplicate_rows():
    case = build_cases()[0]
    task = task_for(case)
    result = process_candidate("text2sql", task, {"confidence":1, "sql":"SELECT DISTINCT name FROM customers WHERE city='Taipei'"})
    assert not ev.grade(case, task, result)["passed"]


def test_sql_evaluation_bounds_recursive_queries():
    with pytest.raises(Exception):
        ev._sql_rows("CREATE TABLE t(x INTEGER);", "", "WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x) SELECT n FROM x WHERE n<0")


def test_python_public_example_alone_does_not_pass():
    case = next(c for c in build_cases() if c["id"] == "code-stable_unique")
    task = task_for(case)
    result = process_candidate("code-author", task, {"confidence":1, "code":"def stable_unique(items):\n    return [2,1]\n"})
    assert not ev.grade(case, task, result)["passed"]


def test_python_correct_return_with_mutated_input_fails():
    case = next(c for c in build_cases() if c["id"] == "code-stable_unique")
    task = task_for(case)
    code = "def stable_unique(items):\n    out=list(dict.fromkeys(items))\n    items.clear()\n    return out\n"
    result = process_candidate("code-author", task, {"confidence":1, "code":code})
    assert not ev.grade(case, task, result)["passed"]


def test_bug_verdict_without_expected_defect_does_not_pass():
    case = next(c for c in build_cases() if c["id"] == "bug-mean-buggy")
    task = task_for(case)
    result = reference(case, task)
    result["bugs"][0]["description"] = "Incorrect indentation"
    assert not ev.grade(case, task, result)["passed"]
    result = reference(case, task)
    result["bugs"].append(deepcopy(result["bugs"][0]))
    assert not ev.grade(case, task, result)["passed"]


def test_reviewer_empty_findings_cannot_pass_positive_gold():
    case = next(c for c in build_cases() if c["id"] == "review-eval")
    task = task_for(case)
    result = {"task_id": task["task_id"], "confidence":1, "verdict":"clean", "findings":[]}
    graded = ev.grade(case, task, result)
    assert not graded["passed"] and graded["finding_fn"] == 1


def test_plan_is_repeatable_and_rounds_have_every_case_once():
    cases = build_cases()
    plan = ev.make_plan(cases, 3, 42)
    assert plan == ev.make_plan(cases, 3, 42)
    assert plan != ev.make_plan(cases, 3, 43)
    for n in range(1, 4):
        assert len({p["case_id"] for p in plan if p["repeat"] == n}) == 40
    assert len({(p["case_id"], p["repeat"]) for p in plan}) == 120


@pytest.mark.parametrize("name,args,expected", [
    ("mean", [[]], None),
    ("last-index", [[2,1,2],2], 2),
    ("inclusive-sum", [3], 6),
    ("all-positive", [[1,-1]], False),
    ("copy-append", [[1],2], [1,2]),
])
def test_bug_pairs_reproduce_real_behavioral_defects(name, args, expected):
    cases = {c["id"]: c for c in build_cases()}
    for buggy in (False, True):
        case = cases["bug-"+name+("-buggy" if buggy else "-clean")]
        scope = {}
        # Only our fixed, authored sources; no model or third-party code here.
        exec(case["task"]["code"], scope)
        function = next(v for k,v in scope.items() if k != "__builtins__" and callable(v))
        inputs = deepcopy(args)
        try:
            actual = function(*inputs)
            correct = actual == expected and inputs == args
        except ZeroDivisionError:
            correct = False
        assert correct is not buggy


def test_checkpoint_resume_never_retries_recorded_attempts(tmp_path):
    cases = [build_cases()[0]]
    meta = manifest(cases)
    seen = []
    def fake(skill, task, **kwargs):
        assert "oracle" not in task
        seen.append(task["task_id"])
        return HermesRun("success", 0, "", "", reference(cases[0], task))
    output = tmp_path/"run.json"
    report = ev.run_evaluation(cases, meta, output=output, invoke=fake, max_invocations=1)
    assert not report["complete"] and report["overall"]["unrun"] == 2
    assert report["overall"]["completed_repeated_tasks"] == 0
    report = ev.run_evaluation(cases, meta, output=output, invoke=fake, resume=True)
    assert report["complete"] and report["overall"]["passed"] == 3
    assert report["overall"]["tasks_passing_all_repeats"] == 1
    assert len(seen) == len(set(seen)) == 3
    assert report["mode"] == "offline-harness-test"
    assert report["unmeasured"]["first_candidate_success_rate"] is None


@pytest.mark.parametrize("status", ["timeout","tool_error","invalid_result"])
def test_failures_remain_in_denominator_and_stop_without_retry(tmp_path, status):
    cases = [build_cases()[0]]
    meta = manifest(cases, repeats=5)
    def fake(*args, **kwargs):
        return HermesRun(status, 1, "SECRET-stdout", "SECRET-stderr", None, "SECRET-error")
    output = tmp_path/"run.json"
    report = ev.run_evaluation(cases, meta, output=output, invoke=fake, stop_after_failures=2)
    assert report["overall"]["recorded"] == 2 and report["overall"]["failed"] == 2
    assert report["overall"]["unrun"] == 3
    assert report["stop_reason"] == "consecutive_failure_limit"
    assert "SECRET" not in output.read_text()


def test_resume_refuses_different_model_or_repetitions(tmp_path):
    cases = [build_cases()[0]]
    output = tmp_path/"run.json"
    meta = manifest(cases)
    ev.run_evaluation(cases, meta, output=output, invoke=lambda *a, **k: HermesRun("timeout",None,"","",None), max_invocations=1)
    changed = dict(meta, requested_model="another")
    with pytest.raises(ValueError, match="manifest differs"):
        ev.run_evaluation(cases, changed, output=output, resume=True)
    with pytest.raises(ValueError, match="already exists"):
        ev.run_evaluation(cases, meta, output=output)


def test_interrupted_call_is_checkpointed_and_not_retried(tmp_path):
    cases = [build_cases()[0]]
    output = tmp_path/"run.json"
    meta = manifest(cases, repeats=1)
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        ev.run_evaluation(cases, meta, output=output, invoke=interrupted)
    state = json.loads(output.read_text())
    assert state["rows"][0]["failure_category"] == "interrupted"
    def should_not_run(*a, **k):
        raise AssertionError("unexpected retry")
    report = ev.run_evaluation(cases, meta, output=output, invoke=should_not_run, resume=True)
    assert report["complete"] and report["overall"]["failed"] == 1


def test_bug_metrics_show_ungraded_runs_and_false_positives():
    cases = [c for c in build_cases() if c["skill"] == "bug-hunter"][:3]
    meta = manifest(cases, repeats=1)
    rows = []
    for i,c in enumerate(cases):
        rows.append({"case_id":c["id"], "skill":"bug-hunter", "repeat":1, "seconds":i+1,
                     "passed":i==0, "failure_category":None if i==0 else "answer_mismatch",
                     "grade":{} if i==2 else {"expected_buggy":c["oracle"]["buggy"], "predicted_buggy":True}})
    report = ev.summarize(meta, rows)
    metrics = report["bug_verdict_metrics"]
    assert metrics["tp"] == metrics["fp"] == metrics["ungraded_runs"] == 1
    assert metrics["precision"] == .5 and metrics["recall"] == 1
    assert report["overall"]["latency_all_recorded"]["median_seconds"] == 2
    assert report["overall"]["latency_all_recorded"]["p95_seconds"] == 2.9


def test_lock_blocks_concurrent_writers_and_cleans_up(tmp_path):
    output = tmp_path/"run.json"
    with ev.output_lock(output):
        with pytest.raises(FileExistsError):
            with ev.output_lock(output):
                pass
    assert not Path(str(output)+".lock").exists()


def test_dry_run_does_not_call_hermes(monkeypatch, capsys):
    monkeypatch.setattr(ev.shutil, "which", lambda _: pytest.fail("dry-run queried Hermes"))
    assert ev.main(["--dry-run"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["planned_agent_invocations"] == 120 and output["agent_invocations"] == 0
    assert output["distinct_tasks"] == 40


def test_missing_hermes_is_blocked_not_mocked(monkeypatch, capsys):
    monkeypatch.setattr(ev.shutil, "which", lambda _: None)
    monkeypatch.setattr(ev, "_source_identity", lambda: {"commit":"a"*40, "tracked_worktree_dirty":False, "source_sha256":"fixed"})
    assert ev.main(["--live", "--model", "test-model"]) == 2
    assert json.loads(capsys.readouterr().out)["agent_invocations"] == 0


def test_source_change_during_invocation_is_failure_and_stops(tmp_path, monkeypatch):
    cases = [build_cases()[0]]
    meta = dict(manifest(cases), source={"source_sha256":"before"})
    identities = iter([meta["source"], {"source_sha256":"after"}])
    monkeypatch.setattr(ev, "_source_identity", lambda: next(identities))
    def fake(skill, task, **kwargs):
        return HermesRun("success",0,"","",reference(cases[0],task))
    report = ev.run_evaluation(cases, meta, output=tmp_path/"run.json", invoke=fake)
    assert report["stop_reason"] == "source_changed"
    assert report["overall"]["failed"] == 1 and report["overall"]["unrun"] == 2


def test_dirty_checkout_is_blocked_before_hermes(monkeypatch, capsys):
    monkeypatch.setattr(ev, "_source_identity", lambda: {"commit":"a"*40, "tracked_worktree_dirty":True, "source_sha256":"fixed"})
    monkeypatch.setattr(ev.shutil, "which", lambda _: pytest.fail("queried Hermes despite dirty checkout"))
    assert ev.main(["--live", "--model", "test-model"]) == 2
    assert json.loads(capsys.readouterr().out)["agent_invocations"] == 0
