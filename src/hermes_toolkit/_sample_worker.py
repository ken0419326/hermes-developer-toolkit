"""Private subprocess worker for executing candidate Python samples.

This process boundary and timeout reduce accidental hangs and isolate globals
from the caller. They are not a security sandbox for hostile code.
"""

from __future__ import annotations

import json
import sys
import traceback


def main() -> int:
    payload = json.load(sys.stdin)
    namespace: dict[str, object] = {"__builtins__": __builtins__}
    try:
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
        print(json.dumps({"ok": True, "value": value}, ensure_ascii=False))
        return 0
    except BaseException as exc:
        print(json.dumps({
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(limit=8),
        }, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
