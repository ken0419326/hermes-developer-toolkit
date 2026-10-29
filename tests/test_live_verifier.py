import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from hermes_toolkit.pipeline import process_candidate


spec = importlib.util.spec_from_file_location("verify_live", Path(__file__).resolve().parents[1] / "scripts/verify_live.py")
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


def valid_invoke(skill, task, **_):
    if skill == "text2sql":
        candidate = {"sql": "SELECT d.name FROM developers d JOIN teams t ON d.team_id=t.id WHERE t.name='AI Platform'", "confidence": 1.0}
    elif skill == "code-author":
        candidate = {"code": "def clamp(value, low, high):\n    return max(low, min(value, high))\n", "confidence": 1.0}
    elif skill == "bug-hunter":
        buggy = "if not items" not in task["code"]
        candidate = {"verdict": "buggy" if buggy else "clean", "bugs": [{"line_start": 2, "line_end": 2, "severity": "medium", "type": "edge_case", "description": "Empty lists raise IndexError."}] if buggy else [], "confidence": 1.0}
    else:
        candidate = None
    return SimpleNamespace(status="success", result=process_candidate(skill, task, candidate), error="")


def test_live_verifier_all_cases_with_test_double():
    report = live.run_suite(invoke=valid_invoke, label="offline-test-double")
    assert report["all_passed"]
    assert len(report["cases"]) == 5
    assert all(not r["designated_tool_call_proven"] for r in report["cases"])


@pytest.mark.parametrize("status", ["timeout", "tool_error", "invalid_result"])
def test_live_verifier_rejects_failed_invocations(status):
    report = live.run_suite(invoke=lambda *_args, **_kwargs: SimpleNamespace(status=status, result=None, error="test failure"), label="offline-test-double")
    assert not report["all_passed"]
    assert all(r["status"] == "FAIL" for r in report["cases"])


def test_sql_compilation_does_not_imply_correct_answer():
    case = live.build_cases("test")[0]
    assert not live.check_result(case, {"sql": "SELECT name FROM developers"})[0]


def test_sql_bag_comparison_accepts_reordered_rows():
    case = live.build_cases("test")[0]
    assert live.check_result(case, {"sql": "SELECT name FROM developers WHERE team_id=1 ORDER BY name DESC"})[0]


def test_extra_code_cases_detect_overfit_public_samples():
    case = live.build_cases("test")[1]
    assert not live.check_result(case, {"code": "def clamp(value, low, high):\n    return max(0, min(value, 10))\n"})[0]


def test_bug_report_must_locate_and_describe_actual_defect():
    case = live.build_cases("test")[2]
    assert not live.check_result(case, {"verdict": "buggy", "bugs": []})[0]


def test_known_correct_code_must_not_be_reported_buggy():
    case = live.build_cases("test")[3]
    assert not live.check_result(case, {"verdict": "buggy", "bugs": []})[0]


def test_dry_run_makes_no_model_calls(capsys):
    assert live.main(["--dry-run"]) == 0
    assert '"model_calls": 0' in capsys.readouterr().out


def test_missing_hermes_is_blocked(monkeypatch, capsys):
    monkeypatch.setattr(live.shutil, "which", lambda _: None)
    assert live.main(["--live"]) == 2
    assert '"status": "BLOCKED"' in capsys.readouterr().out
