from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict


WRITE_ACTION_NAMES = (
    "SQLITE_ALTER_TABLE", "SQLITE_ANALYZE", "SQLITE_ATTACH", "SQLITE_CREATE_INDEX",
    "SQLITE_CREATE_TABLE", "SQLITE_CREATE_TEMP_INDEX", "SQLITE_CREATE_TEMP_TABLE",
    "SQLITE_CREATE_TEMP_TRIGGER", "SQLITE_CREATE_TEMP_VIEW", "SQLITE_CREATE_TRIGGER",
    "SQLITE_CREATE_VIEW", "SQLITE_DELETE", "SQLITE_DETACH", "SQLITE_DROP_INDEX",
    "SQLITE_DROP_TABLE", "SQLITE_DROP_TEMP_INDEX", "SQLITE_DROP_TEMP_TABLE",
    "SQLITE_DROP_TEMP_TRIGGER", "SQLITE_DROP_TEMP_VIEW", "SQLITE_DROP_TRIGGER",
    "SQLITE_DROP_VIEW", "SQLITE_INSERT", "SQLITE_PRAGMA", "SQLITE_REINDEX",
    "SQLITE_TRANSACTION", "SQLITE_UPDATE",
)
WRITE_ACTIONS = {getattr(sqlite3, name) for name in WRITE_ACTION_NAMES if hasattr(sqlite3, name)}


@dataclass(frozen=True)
class SQLValidation:
    ok: bool
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _first_keyword(sql: str) -> str:
    """Return the first SQL word while lexically skipping whitespace/comments."""
    index, size = 0, len(sql)
    while index < size:
        if sql[index].isspace():
            index += 1
            continue
        if sql.startswith("--", index):
            newline = sql.find("\n", index + 2)
            index = size if newline < 0 else newline + 1
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            if end < 0:
                return ""
            index = end + 2
            continue
        break
    start = index
    while index < size and (sql[index].isalpha() or sql[index] == "_"):
        index += 1
    return sql[start:index].upper()


def validate_sql(schema_ddl: str, sql: str) -> SQLValidation:
    if not isinstance(schema_ddl, str):
        return SQLValidation(False, "schema_ddl must be a string")
    if not isinstance(sql, str) or not sql.strip():
        return SQLValidation(False, "SQL must be a non-empty string")
    if _first_keyword(sql) not in {"SELECT", "WITH"}:
        return SQLValidation(False, "only read-only SELECT or WITH queries are allowed")

    connection = sqlite3.connect(":memory:")
    denied: list[int] = []

    def authorize(action: int, _arg1: str | None, _arg2: str | None, _db: str | None, _source: str | None) -> int:
        if action in WRITE_ACTIONS:
            denied.append(action)
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    try:
        connection.executescript(schema_ddl)
        connection.execute("PRAGMA query_only = ON")
        connection.set_authorizer(authorize)
        # sqlite3.execute delegates statement boundaries and SQL lexical rules
        # to SQLite, so semicolons and keywords inside literals/comments remain
        # data while a real second statement is rejected.
        connection.execute(f"EXPLAIN {sql.strip()}")
    except sqlite3.Error as exc:
        if denied:
            return SQLValidation(False, "only read-only SELECT statements are allowed")
        if "one statement" in str(exc).lower():
            return SQLValidation(False, "exactly one SQL statement is allowed")
        return SQLValidation(False, f"SQLite validation failed: {exc}")
    finally:
        connection.close()
    return SQLValidation(True)
