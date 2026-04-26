"""
Database Adapter — Unified SQLite / PostgreSQL interface.

MIGRATION NOTE:
  Local dev:  SQLite (default, file-based)
  Production: PostgreSQL via DATABASE_URL (Supabase, Render, etc.)

SQL Compatibility:
  - Placeholders: '?' → automatically converted to '%s' for PostgreSQL
  - AUTOINCREMENT → SERIAL (handled in init_schema)
  - row_factory / sqlite3.Row → RealDictCursor (psycopg2) or sqlite3.Row
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# PostgreSQL support (optional dependency)
# ---------------------------------------------------------------------------
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import SimpleConnectionPool

    _HAS_PSYCOPG2 = True
except ImportError:
    _HAS_PSYCOPG2 = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Priority: DATABASE_URL (production) > KIMI_DB_PATH (legacy/local)
DB_URL = os.environ.get("DATABASE_URL") or os.environ.get(
    "KIMI_DB_PATH", "sqlite:///data/dashboard.db"
)

# Connection pool for PostgreSQL (created lazily)
_pool: Optional[Any] = None


def is_postgres() -> bool:
    """Return True if the configured database is PostgreSQL."""
    return DB_URL.startswith(("postgres://", "postgresql://"))


def _get_db_path() -> str:
    """Extract filesystem path from sqlite:/// URI."""
    if DB_URL.startswith("sqlite:///"):
        return DB_URL[10:]
    return DB_URL


# ---------------------------------------------------------------------------
# Connection Management
# ---------------------------------------------------------------------------

def _init_pool() -> Any:
    """Initialize PostgreSQL connection pool."""
    global _pool
    if _pool is None and _HAS_PSYCOPG2:
        _pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DB_URL,
        )
    return _pool


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    """
    Yield a database connection (SQLite or PostgreSQL).
    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            ...
    """
    if is_postgres():
        if not _HAS_PSYCOPG2:
            raise RuntimeError(
                "PostgreSQL is configured but psycopg2 is not installed. "
                "Run: pip install psycopg2-binary"
            )
        pool = _init_pool()
        conn = pool.getconn()
        try:
            yield conn
        finally:
            pool.putconn(conn)
    else:
        db_path = _get_db_path()
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Query Helpers
# ---------------------------------------------------------------------------

def _adapt_query(sql: str) -> str:
    """Convert SQLite-flavoured SQL to PostgreSQL-compatible SQL."""
    if not is_postgres():
        return sql

    # Replace standalone '?' placeholders with '%s'.
    # Skip '?' inside string literals.
    result = []
    in_string = False
    string_char = None
    i = 0
    while i < len(sql):
        ch = sql[i]
        if not in_string and ch in ("'", '"'):
            in_string = True
            string_char = ch
            result.append(ch)
        elif in_string and ch == string_char:
            if i + 1 < len(sql) and sql[i + 1] == string_char:
                result.append(ch)
                i += 1
            else:
                in_string = False
                string_char = None
                result.append(ch)
        elif not in_string and ch == "?":
            result.append("%s")
        else:
            result.append(ch)
        i += 1

    return "".join(result)


def _rows_to_dicts(cursor: Any, rows: List[Any]) -> List[Dict[str, Any]]:
    """Normalize fetched rows to plain dicts regardless of driver."""
    if not rows:
        return []
    if is_postgres():
        return [dict(r) for r in rows]
    return [dict(r) for r in rows]


class CursorProxy:
    """Wraps a DB cursor to provide dialect-safe lastrowid / rowcount."""

    def __init__(self, cursor: Any, inserted_id: Optional[int] = None):
        self._cursor = cursor
        self._inserted_id = inserted_id

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def lastrowid(self) -> Optional[int]:
        if self._inserted_id is not None:
            return self._inserted_id
        # sqlite3 cursor has lastrowid
        return getattr(self._cursor, "lastrowid", None)

    def fetchone(self) -> Optional[Any]:
        return self._cursor.fetchone()

    def fetchall(self) -> List[Any]:
        return self._cursor.fetchall()

    @property
    def description(self):
        return self._cursor.description


def execute(
    conn: Any,
    sql: str,
    params: Tuple[Any, ...] = (),
) -> CursorProxy:
    """Execute a statement and return a proxy cursor."""
    adapted_sql = _adapt_query(sql)
    cursor = conn.cursor()
    cursor.execute(adapted_sql, params)

    inserted_id = None
    if is_postgres():
        # psycopg2 cursor does not have lastrowid.
        # If the query was INSERT ... RETURNING id, fetch it.
        if "RETURNING" in adapted_sql.upper() and "INSERT" in adapted_sql.upper():
            row = cursor.fetchone()
            if row:
                inserted_id = row[0] if hasattr(row, "__getitem__") else getattr(row, "id", None)
        # For INSERT without RETURNING, we can't easily get lastrowid in psycopg2
        # unless we add RETURNING id. Callers should prefer RETURNING id.

    return CursorProxy(cursor, inserted_id=inserted_id)


def fetchall(
    conn: Any,
    sql: str,
    params: Tuple[Any, ...] = (),
) -> List[Dict[str, Any]]:
    """Execute SELECT and return list of dicts."""
    proxy = execute(conn, sql, params)
    rows = proxy.fetchall()
    return _rows_to_dicts(proxy._cursor, rows)


def fetchone(
    conn: Any,
    sql: str,
    params: Tuple[Any, ...] = (),
) -> Optional[Dict[str, Any]]:
    """Execute SELECT and return first row as dict, or None."""
    rows = fetchall(conn, sql, params)
    return rows[0] if rows else None


def commit(conn: Any) -> None:
    """Commit current transaction."""
    conn.commit()


# ---------------------------------------------------------------------------
# Schema Initialisation
# ---------------------------------------------------------------------------

SCHEMA_TABLES = [
    (
        "jobs",
        """
            id          SERIAL PRIMARY KEY,
            job_type    TEXT NOT NULL,
            status      TEXT DEFAULT 'pending',
            params      TEXT,
            result      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at  TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            pid         INTEGER,
            script_name TEXT,
            triggered_by TEXT DEFAULT 'dashboard_user'
        """,
        [
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC)",
        ],
        None,
    ),
    (
        "project_state",
        """
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            name        TEXT DEFAULT 'default',
            current_stage TEXT DEFAULT 'l1',
            status      TEXT DEFAULT 'active',
            config      TEXT DEFAULT '{}',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """,
        [],
        {"id": 1, "name": "default", "current_stage": "l1", "status": "active", "config": "{}"},
    ),
    (
        "artifacts_index",
        """
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT NOT NULL,
            path        TEXT NOT NULL,
            size        INTEGER DEFAULT 0,
            task_id     TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum    TEXT
        """,
        [
            "CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts_index(task_id)",
        ],
        None,
    ),
    (
        "audit_log",
        """
            id          SERIAL PRIMARY KEY,
            event_type  TEXT NOT NULL,
            actor       TEXT,
            action      TEXT,
            details     TEXT,
            timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """,
        [
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC)",
        ],
        None,
    ),
]


def _translate_ddl(pg_ddl: str) -> str:
    """Convert the PostgreSQL-oriented DDL in SCHEMA_TABLES to SQLite dialect."""
    sqlite_ddl = pg_ddl
    sqlite_ddl = sqlite_ddl.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    return sqlite_ddl


def init_schema() -> None:
    """Create tables and indexes if they don't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for table_name, pg_columns, indexes, seed in SCHEMA_TABLES:
            if is_postgres():
                ddl = f"CREATE TABLE IF NOT EXISTS {table_name} ({pg_columns})"
            else:
                sqlite_columns = _translate_ddl(pg_columns)
                ddl = f"CREATE TABLE IF NOT EXISTS {table_name} ({sqlite_columns})"

            cursor.execute(ddl)

            for idx_sql in indexes:
                cursor.execute(idx_sql)

            if seed:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                if count == 0:
                    cols = ", ".join(seed.keys())
                    placeholders = ", ".join(["?"] * len(seed))
                    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                    cursor.execute(_adapt_query(sql), tuple(seed.values()))

        conn.commit()


# ---------------------------------------------------------------------------
# FastAPI Dependency
# ---------------------------------------------------------------------------

def get_db():
    """FastAPI dependency that yields a connection and closes it."""
    with get_connection() as conn:
        yield conn
