import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_text2sql_wrapper_works_from_other_directory_with_candidate_file(tmp_path):
    task_path = tmp_path / "task 'quoted' 台灣.json"
    candidate_path = tmp_path / "candidate $dollar.json"
    output_path = tmp_path / "result.json"
    task_path.write_text(json.dumps({
        "task_id": "特殊-'\"-$()",
        "db_schema": "CREATE TABLE notes(text TEXT);",
    }, ensure_ascii=False), encoding="utf-8")
    sql = "SELECT text FROM notes WHERE text = 'single '' quote; \\\"double\\\"\n台灣 $HOME $(date)'"
    candidate_path.write_text(json.dumps({
        "sql": sql,
        "rationale": "quotes ' \" newlines\nUnicode 台灣 and shell $() `ticks`",
        "confidence": 0.8,
    }, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ)
    env.update(
        HERMES_TOOLKIT_TASK_PATH=str(task_path),
        HERMES_TOOLKIT_OUTPUT_PATH=str(output_path),
    )
    process = subprocess.run(
        [sys.executable, str(ROOT / "skills/text2sql/scripts/run.py"), "--candidate", str(candidate_path)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(output_path.read_text(encoding="utf-8"))["sql"] == sql


def test_code_reviewer_wrapper_works_from_other_directory(tmp_path):
    task_path = tmp_path / "task.json"
    output_path = tmp_path / "result.json"
    task_path.write_text(json.dumps({
        "task_id": "review-wrapper", "code": "def run(value):\n    return eval(value)\n",
    }), encoding="utf-8")
    env = dict(os.environ)
    env.update(HERMES_TOOLKIT_TASK_PATH=str(task_path), HERMES_TOOLKIT_OUTPUT_PATH=str(output_path))
    process = subprocess.run(
        [sys.executable, str(ROOT / "skills/code-reviewer/scripts/run.py")],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(output_path.read_text(encoding="utf-8"))["verdict"] == "review_needed"


def test_code_author_wrapper_works_from_other_directory(tmp_path):
    task_path = tmp_path / "code task.json"
    candidate_path = tmp_path / "code candidate.json"
    output_path = tmp_path / "code result.json"
    task_path.write_text(json.dumps({
        "task_id": "code-'\"-$()",
        "constraints": {"entry_function": "echo", "imports_forbidden": []},
        "sample_inputs": [{"input": ["台灣 $HOME ' \"\n"], "expected": "台灣 $HOME ' \"\n"}],
    }, ensure_ascii=False), encoding="utf-8")
    candidate_path.write_text(json.dumps({
        "code": "def echo(value):\n    print(\"debug $() `ticks`\")\n    return value\n",
        "rationale": "preserve ' and \" with Unicode 台灣",
        "confidence": 0.9,
    }, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ)
    env.update(HERMES_TOOLKIT_TASK_PATH=str(task_path), HERMES_TOOLKIT_OUTPUT_PATH=str(output_path))
    process = subprocess.run(
        [sys.executable, str(ROOT / "skills/code-author/scripts/run.py"), "--candidate", str(candidate_path)],
        cwd=tmp_path, env=env, text=True, capture_output=True, timeout=10, check=False,
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["validation"]["samples"][0]["stdout"] == "debug $() `ticks`\n"


def test_bug_hunter_wrapper_works_from_other_directory(tmp_path):
    task_path = tmp_path / "bug task.json"
    candidate_path = tmp_path / "bug candidate.json"
    output_path = tmp_path / "bug result.json"
    task_path.write_text(json.dumps({
        "task_id": "bug-台灣-$()", "code": "def first(items):\n    return items[0]\n",
    }, ensure_ascii=False), encoding="utf-8")
    candidate_path.write_text(json.dumps({
        "verdict": "buggy", "confidence": 0.8,
        "bugs": [{
            "line_start": 2, "line_end": 2, "severity": "medium", "type": "edge_case",
            "description": "Empty input with 'quotes', \"double quotes\", $HOME and 台灣.",
        }],
    }, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ)
    env.update(HERMES_TOOLKIT_TASK_PATH=str(task_path), HERMES_TOOLKIT_OUTPUT_PATH=str(output_path))
    process = subprocess.run(
        [sys.executable, str(ROOT / "skills/bug-hunter/scripts/run.py"), "--candidate", str(candidate_path)],
        cwd=tmp_path, env=env, text=True, capture_output=True, timeout=10, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(output_path.read_text(encoding="utf-8"))["task_id"] == "bug-台灣-$()"
