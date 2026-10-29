import json
import sys

from hermes_toolkit.hermes import invoke_hermes


TASK = {"task_id": "boundary-1", "db_schema": "CREATE TABLE t(x INTEGER);"}


def make_script(tmp_path, body):
    path = tmp_path / "fake_hermes.py"
    path.write_text(body, encoding="utf-8")
    return [sys.executable, str(path)]


def test_successful_hermes_boundary(tmp_path):
    command = make_script(tmp_path, """
import json, os
task = json.load(open(os.environ['HERMES_TOOLKIT_TASK_PATH'], encoding='utf-8'))
out = {'task_id': task['task_id'], 'sql': 'SELECT x FROM t', 'rationale': 'fixture', 'confidence': 1.0}
json.dump(out, open(os.environ['HERMES_TOOLKIT_OUTPUT_PATH'], 'w', encoding='utf-8'))
""")
    run = invoke_hermes("text2sql", TASK, command=command, timeout=2)
    assert run.status == "success"
    assert run.result["task_id"] == "boundary-1"


def test_missing_result_is_reported(tmp_path):
    command = make_script(tmp_path, "print('no result')")
    run = invoke_hermes("text2sql", TASK, command=command, timeout=2)
    assert run.status == "invalid_result"
    assert "not found" in run.error


def test_non_object_result_is_reported(tmp_path):
    command = make_script(tmp_path, """
import json, os
json.dump([], open(os.environ['HERMES_TOOLKIT_OUTPUT_PATH'], 'w'))
""")
    run = invoke_hermes("text2sql", TASK, command=command, timeout=2)
    assert run.status == "invalid_result"
    assert "object" in run.error


def test_tool_failure_is_reported(tmp_path):
    command = make_script(tmp_path, "raise SystemExit(7)")
    run = invoke_hermes("text2sql", TASK, command=command, timeout=2)
    assert run.status == "tool_error"
    assert run.returncode == 7


def test_timeout_is_reported(tmp_path):
    command = make_script(tmp_path, "import time; time.sleep(2)")
    run = invoke_hermes("text2sql", TASK, command=command, timeout=0.1)
    assert run.status == "timeout"
    assert "timed out" in run.error
