from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class InputError(ValueError):
    """Raised when a JSON input cannot be loaded as an object."""


def load_json_object(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"JSON file not found: {source}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError(f"cannot read JSON file {source}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError(f"JSON root must be an object: {source}")
    return value


def parse_json_object(text: str, *, label: str = "input") -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError(f"JSON root must be an object in {label}")
    return value


def atomic_write_json(path: str | Path, value: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
