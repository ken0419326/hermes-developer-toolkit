from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, asdict


FORBIDDEN = re.compile(
    r"\b(ALTER|ATTACH|CREATE|DELETE|DETACH|DROP|INSERT|PRAGMA|REINDEX|REPLACE|TRUNCATE|UPDATE|VACUUM)\b",
    re.IGNORECASE,
)
LEADING_COMMENT = re.compile(r"\A(?:\s|--[^\n]*(?:\n|\Z)|/\*.*?\*/)*", re.DOTALL)


@dataclass(frozen=True)
class SQLValidation:
    ok: bool
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _single_statement(sql: str) -> bool:
    stripped = sql.strip()
    if not stripped:
        return False
    # sqlite3.complete_statement requires a terminator. Removing one trailing
    # semicolon lets us reject any remaining statement separator.
    body = stripped[:-1] if stripped.endswith(";") else stripped
    return ";" not in body


def validate_sql(schema_ddl: str, sql: str) -> SQLValidation:
    if not isinstance(schema_ddl, str):
        return SQLValidation(False, "schema_ddl must be a string")
    if not isinstance(sql, str) or not sql.strip():
        return SQLValidation(False, "SQL must be a non-empty string")
    if not _single_statement(sql):
        return SQLValidation(False, "exactly one SQL statement is allowed")
    if FORBIDDEN.search(sql):
        return SQLValidation(False, "only read-only SELECT statements are allowed")
    prefix_removed = LEADING_COMMENT.sub("", sql, count=1).lstrip()
    if not re.match(r"(?is)^(SELECT|WITH)\b", prefix_removed):
        return SQLValidation(False, "query must start with SELECT or WITH")

    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(schema_ddl)
        connection.execute("PRAGMA query_only = ON")
        connection.execute(f"EXPLAIN {sql.strip().rstrip(';')}")
    except sqlite3.Error as exc:
        return SQLValidation(False, f"SQLite validation failed: {exc}")
    finally:
        connection.close()
    return SQLValidation(True)
