import json

import pytest

from hermes_toolkit.io import InputError, atomic_write_json, load_json_object, parse_json_object


def test_atomic_write_preserves_unicode_quotes_and_newlines(tmp_path):
    path = tmp_path / "nested" / "result.json"
    value = {"text": "台灣 \"AI\"\nnext line"}
    atomic_write_json(path, value)
    assert json.loads(path.read_text(encoding="utf-8")) == value
    assert not list(path.parent.glob("*.tmp"))


def test_atomic_write_replaces_existing_file(tmp_path):
    path = tmp_path / "result.json"
    path.write_text("old", encoding="utf-8")
    atomic_write_json(path, {"ok": True})
    assert load_json_object(path) == {"ok": True}


def test_missing_file_has_clear_error(tmp_path):
    with pytest.raises(InputError, match="not found"):
        load_json_object(tmp_path / "missing.json")


@pytest.mark.parametrize("text", ["[]", '"text"', "null"])
def test_json_root_must_be_object(text):
    with pytest.raises(InputError, match="object"):
        parse_json_object(text)


def test_invalid_json_rejected():
    with pytest.raises(InputError, match="invalid JSON"):
        parse_json_object("{broken")
