#!/usr/bin/env python3
"""Offline demonstration using checked-in fixture model outputs.

No model is called. The fixture candidates demonstrate the deterministic
contract and validation boundary that would receive real model output.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hermes_toolkit.io import load_json_object
from hermes_toolkit.pipeline import process_candidate


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("text2sql", "text2sql.json", "text2sql_candidate.json"),
    ("code-author", "code_author.json", "code_author_candidate.json"),
    ("bug-hunter", "bug_hunter.json", "bug_hunter_candidate.json"),
    ("code-reviewer", "code_reviewer.json", None),
)


def main() -> int:
    print("OFFLINE DEMO: model outputs are fixtures; no Hermes or LLM is called.\n")
    with tempfile.TemporaryDirectory(prefix="hermes_toolkit_demo_") as directory:
        for skill, task_name, fixture_name in CASES:
            task = load_json_object(ROOT / "examples" / "tasks" / task_name)
            candidate = (
                load_json_object(ROOT / "examples" / "fixtures" / fixture_name)
                if fixture_name else None
            )
            output = Path(directory) / f"{skill}.json"
            result = process_candidate(skill, task, candidate, output_path=output)
            print(f"[{skill}] validated and atomically written")
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
