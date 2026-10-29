"""Private subprocess worker for executing candidate Python samples.

This process boundary and timeout reduce accidental hangs and isolate globals
from the caller. They are not a security sandbox for hostile code.
"""

from __future__ import annotations

import json
import io
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout


def main() -> int:
    payload = json.load(sys.stdin)
    namespace: dict[str, object] = {"__builtins__": __builtins__}
    candidate_stdout = io.StringIO()
    candidate_stderr = io.StringIO()
    try:
        with redirect_stdout(candidate_stdout), redirect_stderr(candidate_stderr):
            compiled = compile(payload["code"], "<candidate>", "exec")
            exec(compiled, namespace)
            function = namespace.get(payload["entry_function"])
            if not callable(function):
                raise TypeError(f"entry function {payload['entry_function']!r} was not defined")
            args = payload.get("args", [])
            kwargs = payload.get("kwargs", {})
            if not isinstance(args, list) or not isinstance(kwargs, dict):
                raise TypeError("sample args must be an array and kwargs must be an object")
            value = function(*args, **kwargs)
        response = {"ok": True, "value": value}
        returncode = 0
    except BaseException as exc:
        response = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(limit=8),
        }
        returncode = 1
    response.update(stdout=candidate_stdout.getvalue(), stderr=candidate_stderr.getvalue())
    sys.stdout.write(json.dumps(response, ensure_ascii=False))
    sys.stdout.write("\n")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
