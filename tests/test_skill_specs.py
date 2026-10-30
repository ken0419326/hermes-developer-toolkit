from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("text2sql", "code-author", "bug-hunter", "code-reviewer")


@pytest.mark.parametrize("skill", SKILLS)
def test_skill_uses_authoritative_task_and_absolute_script_path(skill):
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "HERMES_TOOLKIT_TASK_PATH" in text
    assert "${HERMES_SKILL_DIR}/scripts/run.py" in text
    assert "python3 scripts/run.py" not in text
    assert "printf '%s'" not in text


@pytest.mark.parametrize("skill", ("text2sql", "code-author", "bug-hunter"))
def test_candidate_skill_uses_file_transport(skill):
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "HERMES_TOOLKIT_CANDIDATE_PATH" in text
    assert "--candidate" in text
    assert "<<'HERMES_CANDIDATE_JSON'" in text


def test_bug_hunter_documents_complete_candidate_contract():
    text = (ROOT / "skills" / "bug-hunter" / "SKILL.md").read_text(encoding="utf-8")
    for field in ("line_start", "line_end", "severity", "type", "description", "verdict", "bugs", "confidence"):
        assert f'"{field}"' in text or f'`{field}`' in text
    for value in (
        "api_misuse", "edge_case", "logic_error", "null_deref", "off_by_one",
        "type_error", "unhandled_input", "unsafe_operation",
        "critical", "high", "medium", "low", "info",
    ):
        assert f"`{value}`" in text
    assert "`line` is not a valid substitute" in text
    assert "Do not\n   stop after fixing only the first reported error" in text
