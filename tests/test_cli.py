import json
import os
import subprocess
import sys


def run_cli(task_path, output_path, stdin, skill="text2sql"):
    env = dict(os.environ)
    env.update(HERMES_TOOLKIT_TASK_PATH=str(task_path), HERMES_TOOLKIT_OUTPUT_PATH=str(output_path))
    return subprocess.run(
        [sys.executable, "-m", "hermes_toolkit.cli", "--skill", skill],
        input=stdin,
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
        check=False,
    )


def test_cli_reads_candidate_from_stdin_without_shell_quoting(tmp_path):
    task = tmp_path / "task.json"
    output = tmp_path / "output.json"
    task.write_text(json.dumps({
        "task_id": "quote-1",
        "db_schema": "CREATE TABLE notes(text TEXT);",
    }), encoding="utf-8")
    candidate = {
        "sql": "SELECT text FROM notes WHERE text = 'line 1\n\"quoted\" 台灣'",
        "rationale": "preserve quotes and newlines",
        "confidence": 0.8,
    }
    process = run_cli(task, output, json.dumps(candidate, ensure_ascii=False))
    assert process.returncode == 0, process.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["sql"] == candidate["sql"]


def test_cli_invalid_json_fails_without_output(tmp_path):
    task = tmp_path / "task.json"
    output = tmp_path / "output.json"
    task.write_text('{"task_id":"x","db_schema":""}', encoding="utf-8")
    process = run_cli(task, output, "{bad")
    assert process.returncode == 1
    assert "invalid JSON" in process.stderr
    assert not output.exists()
