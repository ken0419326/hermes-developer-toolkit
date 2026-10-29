import pytest

from hermes_toolkit.contracts import ContractError, validate_result


TASK = {"task_id": "任務-1", "code": "def f(x):\n    return x\n"}


def test_text2sql_contract_accepts_unicode_task_id():
    value = validate_result("text2sql", TASK, {
        "task_id": "任務-1", "sql": "SELECT '測試'", "rationale": "ok", "confidence": 0.5,
    })
    assert value["task_id"] == "任務-1"


@pytest.mark.parametrize("bad", [None, [], "x", 1])
def test_result_must_be_object(bad):
    with pytest.raises(ContractError, match="object"):
        validate_result("text2sql", TASK, bad)


def test_task_id_mismatch_rejected():
    with pytest.raises(ContractError, match="mismatch"):
        validate_result("text2sql", TASK, {
            "task_id": "wrong", "sql": "SELECT 1", "rationale": "", "confidence": 0.5,
        })


@pytest.mark.parametrize("confidence", [True, "0.5", -0.1, 1.1, float("nan")])
def test_confidence_type_and_range(confidence):
    with pytest.raises(ContractError, match="confidence"):
        validate_result("text2sql", TASK, {
            "task_id": "任務-1", "sql": "SELECT 1", "rationale": "", "confidence": confidence,
        })


def test_clean_bug_report_must_be_empty():
    with pytest.raises(ContractError, match="empty"):
        validate_result("bug-hunter", TASK, {
            "task_id": "任務-1", "verdict": "clean", "confidence": 0.8,
            "bugs": [{
                "line_start": 1, "line_end": 1, "severity": "low", "type": "logic_error",
                "description": "contradiction",
            }],
        })


def test_bug_location_must_be_in_source():
    with pytest.raises(ContractError, match="past"):
        validate_result("bug-hunter", TASK, {
            "task_id": "任務-1", "verdict": "buggy", "confidence": 0.8,
            "bugs": [{
                "line_start": 9, "line_end": 9, "severity": "high", "type": "logic_error",
                "description": "outside source",
            }],
        })


def test_missing_required_field_rejected():
    with pytest.raises(ContractError, match="sql"):
        validate_result("text2sql", TASK, {
            "task_id": "任務-1", "rationale": "", "confidence": 0.5,
        })
