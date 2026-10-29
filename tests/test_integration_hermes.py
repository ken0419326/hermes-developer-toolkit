import os
import shutil

import pytest

from hermes_toolkit.hermes import invoke_hermes


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("HERMES_INTEGRATION") != "1" or shutil.which("hermes") is None,
    reason="set HERMES_INTEGRATION=1 with a configured Hermes CLI and real provider",
)
def test_real_hermes_text2sql_contract():
    task = {
        "task_id": "integration-sql-1",
        "question": "Return every developer name.",
        "db_schema": "CREATE TABLE developers(name TEXT);",
        "dialect": "sqlite",
    }
    run = invoke_hermes("text2sql", task)
    assert run.status == "success", run.error
