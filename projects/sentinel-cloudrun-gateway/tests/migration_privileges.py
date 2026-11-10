"""Prove the migration role can provision a restricted runtime DB role."""
import os
import subprocess

PROJECT = os.getenv("COMPOSE_PROJECT_NAME")
if not PROJECT:
    raise SystemExit("Run only from an isolated Compose project")


def compose(*args):
    result = subprocess.run(["docker", "compose", *args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


compose("exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-U", "sentinel", "-d", "sentinel", "-c",
        "DO $$ BEGIN CREATE ROLE sentinel_runtime; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
compose("exec", "-T", "gateway", "python", "-c",
        "import os; from sentinel.migrations import apply_migrations; apply_migrations(os.environ['DATABASE_URL'], 'sentinel_runtime')")
rows = compose("exec", "-T", "db", "psql", "-At", "-F", ",", "-U", "sentinel", "-d", "sentinel", "-c", """
SELECT has_table_privilege('sentinel_runtime','customers','SELECT'),
       has_table_privilege('sentinel_runtime','customers','UPDATE'),
       has_table_privilege('sentinel_runtime','customers','DELETE'),
       has_table_privilege('sentinel_runtime','documents','SELECT'),
       has_table_privilege('sentinel_runtime','documents','INSERT'),
       has_table_privilege('sentinel_runtime','audit_events','INSERT'),
       has_table_privilege('sentinel_runtime','audit_events','UPDATE'),
       has_table_privilege('sentinel_runtime','schema_migrations','SELECT'),
       has_schema_privilege('sentinel_runtime','public','CREATE');
""")
expected = "t,t,f,t,f,t,f,t,f"
assert rows == expected, rows
print("PASS: migration applied; runtime role has least-privilege table grants, audit append-only access, and no schema CREATE")
