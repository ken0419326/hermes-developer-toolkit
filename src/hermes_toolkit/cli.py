from __future__ import annotations

import argparse
import json
import os
import sys

from .contracts import SKILLS
from .io import InputError, load_json_object, parse_json_object
from .pipeline import PipelineError, process_candidate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and write Hermes skill results")
    parser.add_argument("--skill", required=True, choices=sorted(SKILLS))
    parser.add_argument("--task", help="task JSON path; defaults to HERMES_TOOLKIT_TASK_PATH")
    parser.add_argument("--candidate", help="candidate JSON path; omit to read one JSON object from stdin")
    parser.add_argument("--output", help="output path; defaults to HERMES_TOOLKIT_OUTPUT_PATH")
    parser.add_argument("--sample-timeout", type=float, default=2.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    task_path = args.task or os.environ.get("HERMES_TOOLKIT_TASK_PATH")
    output_path = args.output or os.environ.get("HERMES_TOOLKIT_OUTPUT_PATH")
    if not task_path or not output_path:
        print("ERROR: task and output paths are required", file=sys.stderr)
        return 2
    try:
        task = load_json_object(task_path)
        if args.skill == "code-reviewer":
            candidate = None
        elif args.candidate:
            candidate = load_json_object(args.candidate)
        else:
            candidate = parse_json_object(sys.stdin.read(), label="stdin")
        result = process_candidate(
            args.skill,
            task,
            candidate,
            output_path=output_path,
            sample_timeout=args.sample_timeout,
        )
    except (InputError, PipelineError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "task_id": result["task_id"], "output": output_path}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
