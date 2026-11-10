"""Exercise PostgreSQL logical backup and restore in an isolated disposable database."""
import os
import subprocess


def compose(*args):
    return subprocess.run(["docker", "compose", *args], check=True, text=True, capture_output=True).stdout.strip()


def counts(database):
    query = "SELECT 'customers='||count(*) FROM customers UNION ALL SELECT 'documents='||count(*) FROM documents UNION ALL SELECT 'approvals='||count(*) FROM approvals UNION ALL SELECT 'audit_events='||count(*) FROM audit_events UNION ALL SELECT 'schema_migrations='||count(*) FROM schema_migrations"
    result = compose("exec", "-T", "db", "psql", "-At", "-U", "sentinel", "-d", database, "-c", query)
    return sorted(result.splitlines())


if not os.getenv("COMPOSE_PROJECT_NAME"):
    raise SystemExit("Run only from an isolated Compose project")

compose("exec", "-T", "db", "pg_dump", "-U", "sentinel", "-d", "sentinel", "-Fc", "-f", "/tmp/sentinel.dump")
compose("exec", "-T", "db", "createdb", "-U", "sentinel", "sentinel_restore")
compose("exec", "-T", "db", "pg_restore", "-U", "sentinel", "-d", "sentinel_restore", "--no-owner", "--no-privileges", "/tmp/sentinel.dump")
source, restored = counts("sentinel"), counts("sentinel_restore")
assert source == restored, (source, restored)
restore_url = "postgresql://sentinel:local-only@db:5432/sentinel_restore"
compose("exec", "-T", "gateway", "env", f"DATABASE_URL={restore_url}", "python", "tools/verify_audit_db.py")
compose("exec", "-T", "db", "dropdb", "-U", "sentinel", "sentinel_restore")
compose("exec", "-T", "db", "rm", "-f", "/tmp/sentinel.dump")
print("PASS: PostgreSQL logical backup restored to a separate disposable database; table counts, migration record, and audit chains matched")
