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


def test_runner_rejects_well_formed_but_destructive_sql(tmp_path):
    command = make_script(tmp_path, """
import json, os
task = json.load(open(os.environ['HERMES_TOOLKIT_TASK_PATH'], encoding='utf-8'))
json.dump({'task_id': task['task_id'], 'sql': 'DROP TABLE t', 'rationale': 'bad', 'confidence': 1.0,
           'validation': {'ok': True}}, open(os.environ['HERMES_TOOLKIT_OUTPUT_PATH'], 'w'))
""")
    run = invoke_hermes("text2sql", TASK, command=command, timeout=2)
    assert run.status == "invalid_result"
    assert "read-only" in run.error


def test_runner_rejects_sql_with_unknown_column(tmp_path):
    command = make_script(tmp_path, """
import json, os
task = json.load(open(os.environ['HERMES_TOOLKIT_TASK_PATH'], encoding='utf-8'))
json.dump({'task_id': task['task_id'], 'sql': 'SELECT invented FROM t', 'rationale': 'bad', 'confidence': 1.0},
          open(os.environ['HERMES_TOOLKIT_OUTPUT_PATH'], 'w'))
""")
    run = invoke_hermes("text2sql", TASK, command=command, timeout=2)
    assert run.status == "invalid_result"
    assert "no such column" in run.error


def test_runner_rejects_python_syntax_error(tmp_path):
    task = {
        "task_id": "code-syntax", "constraints": {"entry_function": "add", "imports_forbidden": []},
        "sample_inputs": [{"input": [1, 2], "expected": 3}],
    }
    command = make_script(tmp_path, """
import json, os
task = json.load(open(os.environ['HERMES_TOOLKIT_TASK_PATH'], encoding='utf-8'))
json.dump({'task_id': task['task_id'], 'code': 'def add(: pass', 'rationale': 'bad', 'confidence': 1.0,
           'validation': {'ok': True}}, open(os.environ['HERMES_TOOLKIT_OUTPUT_PATH'], 'w'))
""")
    run = invoke_hermes("code-author", task, command=command, timeout=2)
    assert run.status == "invalid_result"


def test_runner_rejects_python_sample_mismatch(tmp_path):
    task = {
        "task_id": "code-sample", "constraints": {"entry_function": "add", "imports_forbidden": []},
        "sample_inputs": [{"input": [1, 2], "expected": 3}],
    }
    command = make_script(tmp_path, """
import json, os
task = json.load(open(os.environ['HERMES_TOOLKIT_TASK_PATH'], encoding='utf-8'))
json.dump({'task_id': task['task_id'], 'code': 'def add(a, b):\\n    return a - b\\n', 'rationale': 'bad',
           'confidence': 1.0, 'validation': {'ok': True}}, open(os.environ['HERMES_TOOLKIT_OUTPUT_PATH'], 'w'))
""")
    run = invoke_hermes("code-author", task, command=command, timeout=2)
    assert run.status == "invalid_result"


def test_runner_rejects_forged_code_reviewer_findings(tmp_path):
    task = {"task_id": "review-forged", "code": "def run(value):\n    return eval(value)\n"}
    command = make_script(tmp_path, """
import json, os
task = json.load(open(os.environ['HERMES_TOOLKIT_TASK_PATH'], encoding='utf-8'))
json.dump({'task_id': task['task_id'], 'verdict': 'clean', 'findings': [], 'confidence': 1.0},
          open(os.environ['HERMES_TOOLKIT_OUTPUT_PATH'], 'w'))
""")
    run = invoke_hermes("code-reviewer", task, command=command, timeout=2)
    assert run.status == "invalid_result"
    assert "deterministic" in run.error


def test_runner_preloads_skill_and_explicitly_hands_off_task(tmp_path):
    command = make_script(tmp_path, """
import json, os, sys
assert '-s' in sys.argv and sys.argv[sys.argv.index('-s') + 1] == 'text2sql'
query = sys.argv[sys.argv.index('-q') + 1]
assert os.environ['HERMES_TOOLKIT_TASK_PATH'] in query
task = json.load(open(os.environ['HERMES_TOOLKIT_TASK_PATH'], encoding='utf-8'))
json.dump({'task_id': task['task_id'], 'sql': 'SELECT x FROM t', 'rationale': 'ok', 'confidence': 1.0},
          open(os.environ['HERMES_TOOLKIT_OUTPUT_PATH'], 'w'))
""")
    run = invoke_hermes("text2sql", TASK, command=command, timeout=2)
    assert run.status == "success", run.error
