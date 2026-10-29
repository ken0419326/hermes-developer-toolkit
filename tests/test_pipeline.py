import json

import pytest

from hermes_toolkit.pipeline import PipelineError, process_candidate


SQL_TASK = {
    "task_id": "sql-1",
    "db_schema": "CREATE TABLE people (name TEXT, age INTEGER);",
    "question": "List adult names.",
}


def test_pipeline_injects_original_task_id_and_writes_output(tmp_path):
    output = tmp_path / "out.json"
    result = process_candidate("text2sql", SQL_TASK, {
        "sql": "SELECT name FROM people WHERE age >= 18",
        "rationale": "filter adults",
        "confidence": 0.9,
    }, output_path=output)
    assert result["task_id"] == "sql-1"
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_pipeline_rejects_model_restatement_mismatch(tmp_path):
    output = tmp_path / "out.json"
    with pytest.raises(PipelineError, match="mismatch"):
        process_candidate("text2sql", SQL_TASK, {
            "task_id": "hallucinated",
            "sql": "SELECT name FROM people",
            "rationale": "",
            "confidence": 0.8,
        }, output_path=output)
    assert not output.exists()


def test_invalid_sql_is_never_written(tmp_path):
    output = tmp_path / "out.json"
    with pytest.raises(PipelineError, match="read-only"):
        process_candidate("text2sql", SQL_TASK, {
            "sql": "DROP TABLE people", "rationale": "", "confidence": 0.8,
        }, output_path=output)
    assert not output.exists()


def test_code_author_validation_is_in_actual_pipeline(tmp_path):
    task = {
        "task_id": "code-1",
        "constraints": {"entry_function": "add", "imports_forbidden": ["os"]},
        "sample_inputs": [{"input": [2, 3], "expected": 5}],
    }
    result = process_candidate("code-author", task, {
        "code": "def add(a, b):\n    return a + b\n",
        "rationale": "direct addition",
        "confidence": 0.9,
    }, output_path=tmp_path / "out.json")
    assert result["validation"]["ok"] is True


def test_bad_code_is_never_written(tmp_path):
    task = {
        "task_id": "code-2",
        "constraints": {"entry_function": "add", "imports_forbidden": []},
        "sample_inputs": [{"input": [2, 3], "expected": 5}],
    }
    output = tmp_path / "out.json"
    with pytest.raises(PipelineError, match="validation"):
        process_candidate("code-author", task, {
            "code": "def add(a, b):\n    return a - b\n", "rationale": "", "confidence": 0.5,
        }, output_path=output)
    assert not output.exists()


def test_code_reviewer_ignores_model_candidate_and_is_deterministic():
    task = {"task_id": "review-1", "code": "def first(xs):\n    return xs[0]\n"}
    first = process_candidate("code-reviewer", task, None)
    second = process_candidate("code-reviewer", task, {"invented": "ignored"})
    assert first == second
    assert first["verdict"] == "review_needed"
