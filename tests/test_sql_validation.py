import pytest

from hermes_toolkit.sql_validation import validate_sql


SCHEMA = """
CREATE TABLE developers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  team_id INTEGER
);
CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
"""


@pytest.mark.parametrize("sql", [
    "SELECT name FROM developers",
    "SELECT d.name FROM developers d JOIN teams t ON d.team_id=t.id WHERE t.name='AI';",
    "WITH ai AS (SELECT id FROM teams WHERE name='AI') SELECT name FROM developers WHERE team_id IN ai",
    "-- read only\nSELECT '引號 '' 與 Unicode 測試'",
])
def test_valid_queries(sql):
    assert validate_sql(SCHEMA, sql).ok


@pytest.mark.parametrize("sql", [
    "", "UPDATE developers SET name='x'", "DELETE FROM developers",
    "PRAGMA table_info(developers)", "SELECT 1; SELECT 2", "VALUES (1)",
])
def test_unsafe_or_invalid_shapes_rejected(sql):
    result = validate_sql(SCHEMA, sql)
    assert not result.ok
    assert result.error


def test_unknown_column_rejected():
    result = validate_sql(SCHEMA, "SELECT invented FROM developers")
    assert not result.ok
    assert "no such column" in result.error


def test_bad_schema_reported():
    result = validate_sql("CREATE TABL broken", "SELECT 1")
    assert not result.ok
    assert "SQLite validation failed" in result.error
