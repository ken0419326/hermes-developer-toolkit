from hermes_toolkit.reviewer import review_code


def rule_ids(result):
    return {item["rule_id"] for item in result["findings"]}


def test_unsafe_index_triggers():
    result = review_code("def first(xs):\n    return xs[0]\n")
    assert "unguarded-constant-index" in rule_ids(result)


def test_guarded_index_does_not_trigger():
    code = "def first(xs):\n    if not xs:\n        return None\n    return xs[0]\n"
    assert review_code(code)["findings"] == []


def test_dynamic_execution_triggers():
    result = review_code("def run(command):\n    return eval(command)\n")
    assert "unsafe-dynamic-execution" in rule_ids(result)
    assert result["findings"][0]["certainty"] == "high"


def test_range_minus_one_not_always_a_bug():
    code = "def pairs(xs):\n    return [(xs[i], xs[i+1]) for i in range(len(xs)-1)]\n"
    assert "all-items-range-minus-one" not in rule_ids(review_code(code, "Return adjacent pairs."))


def test_range_minus_one_triggers_with_all_items_requirement():
    code = "def total(xs):\n    out = 0\n    for i in range(len(xs)-1):\n        out += xs[i]\n    return out\n"
    result = review_code(code, "Sum all elements in the input.")
    assert "all-items-range-minus-one" in rule_ids(result)
    assert result["findings"][0]["certainty"] == "medium"


def test_same_input_is_deterministic():
    code = "def first(xs):\n    return xs[0]\n"
    assert review_code(code) == review_code(code)


def test_syntax_error_is_a_finding():
    result = review_code("def broken(: pass")
    assert "python-syntax-error" in rule_ids(result)
