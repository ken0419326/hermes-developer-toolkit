from hermes_toolkit.python_validation import validate_python


def test_python_samples_pass_with_quotes_newlines_and_unicode():
    code = "def normalize(text):\n    return text.strip().replace('\\n', ' / ')\n"
    result = validate_python(
        code,
        entry_function="normalize",
        samples=[{"input": ["  台灣\nAI  "], "expected": "台灣 / AI"}],
    )
    assert result.ok
    assert result.samples[0].passed


def test_sample_mismatch_fails():
    result = validate_python(
        "def add(a, b):\n    return a - b\n",
        entry_function="add",
        samples=[{"input": [3, 2], "expected": 5}],
    )
    assert not result.ok
    assert "expected 5" in result.samples[0].error


def test_syntax_error_fails_before_execution():
    result = validate_python("def broken(: pass", entry_function="broken")
    assert not result.ok
    assert result.syntax_error


def test_missing_entry_function_fails():
    result = validate_python("def other():\n    return 1\n", entry_function="expected")
    assert not result.ok
    assert not result.entry_found


def test_forbidden_import_is_ast_checked():
    result = validate_python(
        "import os.path\ndef f():\n    return 1\n",
        entry_function="f",
        forbidden_imports=["os"],
    )
    assert not result.ok
    assert result.import_violations == ("os",)


def test_allowed_import_is_available_to_generated_function():
    result = validate_python(
        "import math\ndef root(value):\n    return math.sqrt(value)\n",
        entry_function="root",
        forbidden_imports=["os"],
        samples=[{"input": [9], "expected": 3.0}],
    )
    assert result.ok


def test_candidate_exception_is_reported():
    result = validate_python(
        "def first(xs):\n    return xs[0]\n",
        entry_function="first",
        samples=[{"input": [[]], "expected": None}],
    )
    assert not result.ok
    assert "IndexError" in result.samples[0].error


def test_timeout_is_bounded():
    result = validate_python(
        "def spin():\n    while True:\n        pass\n",
        entry_function="spin",
        samples=[{"input": [], "expected": None}],
        timeout=0.1,
    )
    assert not result.ok
    assert "timed out" in result.samples[0].error
