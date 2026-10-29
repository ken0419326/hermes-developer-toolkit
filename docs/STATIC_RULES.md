# Deterministic static-review rules

The code reviewer intentionally has a small, explainable scope. It uses Python's AST and does not execute submitted code.

| Rule | Triggers | Does not claim |
|---|---|---|
| `python-syntax-error` | Source cannot be parsed | That syntactically valid code is correct |
| `unsafe-dynamic-execution` | Direct calls to `eval`, `exec`, or `os.system` | A complete security audit |
| `unguarded-constant-index` | A function indexes a named container at `0` or `-1` without a visible empty guard | That the input is definitely empty; certainty is medium |
| `all-items-range-minus-one` | `range(len(x)-1)` appears and the task explicitly requires all/every items | That the same loop is wrong for adjacent-pair algorithms |

Each rule has positive and negative cases in `tests/test_reviewer.py`. Determinism is checked separately from agreement with annotated cases. Medium-certainty findings are requests for human review, not proof of a defect.
