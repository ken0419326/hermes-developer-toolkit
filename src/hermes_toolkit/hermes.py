from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .contracts import validate_result
from .io import InputError, atomic_write_json, load_json_object
from .pipeline import PipelineError, process_candidate


@dataclass(frozen=True)
class HermesRun:
    status: str
    returncode: int | None
    stdout: str
    stderr: str
    result: dict | None
    error: str = ""


def invoke_hermes(
    skill: str,
    task: dict,
    *,
    command: Sequence[str] = ("hermes", "chat", "--toolsets", "skills,terminal", "--yolo", "-Q"),
    model: str | None = None,
    timeout: float = 240.0,
    sample_timeout: float = 2.0,
) -> HermesRun:
    with tempfile.TemporaryDirectory(prefix="hermes_toolkit_") as directory:
        root = Path(directory)
        task_path = root / "task.json"
        candidate_path = root / "candidate.json"
        result_path = root / "result.json"
        atomic_write_json(task_path, task)
        env = dict(os.environ)
        env.update(
            HERMES_TOOLKIT_TASK_PATH=str(task_path),
            HERMES_TOOLKIT_CANDIDATE_PATH=str(candidate_path),
            HERMES_TOOLKIT_OUTPUT_PATH=str(result_path),
        )
        argv = list(command)
        if model:
            argv.extend(("-m", model))
        prompt = (
            f"Use the preloaded {skill} skill. The original UTF-8 JSON task is at {task_path}. "
            "Read that file with the terminal tool before acting; do not reconstruct the task from this prompt. "
            "Follow the skill's validated file-output procedure and do not claim success unless its tool succeeds."
        )
        argv.extend(("-s", skill, "-q", prompt))
        try:
            process = subprocess.run(
                argv,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            return HermesRun("tool_error", None, "", "", None, str(exc))
        except subprocess.TimeoutExpired as exc:
            return HermesRun(
                "timeout", None, exc.stdout or "", exc.stderr or "", None,
                f"Hermes timed out after {timeout:g}s",
            )
        if process.returncode != 0:
            return HermesRun(
                "tool_error", process.returncode, process.stdout, process.stderr, None,
                f"Hermes exited with status {process.returncode}",
            )
        try:
            supplied = load_json_object(result_path)
            if skill == "code-reviewer":
                supplied = validate_result(skill, task, supplied)
                expected = process_candidate(skill, task, None)
                if supplied != expected:
                    raise PipelineError("code-reviewer result differs from deterministic analysis of the original task")
                result = expected
            else:
                # Re-run deterministic content checks. Any model-provided
                # `validation` object is overwritten and never trusted.
                result = process_candidate(
                    skill, task, supplied, sample_timeout=sample_timeout
                )
        except (InputError, PipelineError, ValueError) as exc:
            return HermesRun("invalid_result", process.returncode, process.stdout, process.stderr, None, str(exc))
        return HermesRun("success", process.returncode, process.stdout, process.stderr, result)
