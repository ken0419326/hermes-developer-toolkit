from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .contracts import validate_result
from .io import InputError, atomic_write_json, load_json_object


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
) -> HermesRun:
    with tempfile.TemporaryDirectory(prefix="hermes_toolkit_") as directory:
        root = Path(directory)
        task_path, result_path = root / "task.json", root / "result.json"
        atomic_write_json(task_path, task)
        env = dict(os.environ)
        env.update(
            HERMES_TOOLKIT_TASK_PATH=str(task_path),
            HERMES_TOOLKIT_OUTPUT_PATH=str(result_path),
        )
        argv = list(command)
        if model:
            argv.extend(("-m", model))
        argv.extend(("-q", f"/{skill}"))
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
            result = load_json_object(result_path)
            result = validate_result(skill, task, result)
        except (InputError, ValueError) as exc:
            return HermesRun("invalid_result", process.returncode, process.stdout, process.stderr, None, str(exc))
        return HermesRun("success", process.returncode, process.stdout, process.stderr, result)
