"""Versioned schema migrations run by an operator-controlled database identity."""
from pathlib import Path

import psycopg
from psycopg import sql

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
RUNTIME_TABLES = ("customers", "documents", "approvals", "idempotency", "call_limits", "audit_events")
RUNTIME_GRANTS = {
    "customers": "SELECT, UPDATE",
    "documents": "SELECT",
    "approvals": "SELECT, INSERT, UPDATE",
    "idempotency": "SELECT, INSERT",
    "call_limits": "SELECT, INSERT, UPDATE",
    "audit_events": "SELECT, INSERT",
}


def apply_migrations(database_url: str, runtime_role: str | None = None) -> list[str]:
    applied: list[str] = []
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            version = migration.stem
            # The first migration creates this table. Bootstrap checks it before use.
            cursor.execute("SELECT to_regclass('public.schema_migrations')")
            if cursor.fetchone()[0] is not None:
                cursor.execute("SELECT 1 FROM schema_migrations WHERE version=%s", (version,))
                if cursor.fetchone():
                    continue
            cursor.execute(migration.read_text(), prepare=False)
            cursor.execute("INSERT INTO schema_migrations(version) VALUES(%s)", (version,))
            applied.append(version)
        cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        cursor.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC")
        cursor.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC")
        if runtime_role:
            if not runtime_role.replace("_", "").isalnum():
                raise ValueError("SENTINEL_RUNTIME_DB_ROLE must be a PostgreSQL identifier")
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (runtime_role,))
            if not cursor.fetchone():
                raise ValueError("Configured runtime database role does not exist")
            role = sql.Identifier(runtime_role)
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
            for table in RUNTIME_TABLES:
                cursor.execute(sql.SQL("REVOKE ALL ON TABLE public.{} FROM PUBLIC").format(sql.Identifier(table)))
                grants = sql.SQL(RUNTIME_GRANTS[table])
                cursor.execute(sql.SQL("GRANT {} ON TABLE public.{} TO {}").format(grants, sql.Identifier(table), role))
            cursor.execute(sql.SQL("GRANT SELECT ON TABLE public.schema_migrations TO {}").format(role))
            sequence = cursor.execute("""
                SELECT n.nspname, c.relname
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE c.oid=pg_get_serial_sequence('public.audit_events','seq')::regclass
            """).fetchone()
            if not sequence:
                raise RuntimeError("Audit event sequence is missing")
            cursor.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE {}.{} TO {}").format(sql.Identifier(sequence[0]), sql.Identifier(sequence[1]), role))
    return applied


def assert_schema_ready(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        version = connection.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1").fetchone()
        if not version or version[0] != "001_initial":
            raise RuntimeError("Required SENTINEL schema migration 001_initial is not applied")
        missing = connection.execute("""
            SELECT name FROM unnest(%s::text[]) AS name
            WHERE to_regclass('public.' || name) IS NULL
        """, (list(RUNTIME_TABLES),)).fetchall()
        if missing:
            raise RuntimeError("Required SENTINEL tables are missing: " + ", ".join(row[0] for row in missing))
