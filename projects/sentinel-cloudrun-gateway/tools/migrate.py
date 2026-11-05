"""Apply SENTINEL database changes using a separate operator identity."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sentinel.migrations import apply_migrations


def main():
    database_url = os.getenv("SENTINEL_MIGRATION_DATABASE_URL", "")
    if not database_url:
        raise SystemExit("Set SENTINEL_MIGRATION_DATABASE_URL to the operator-controlled migration connection")
    versions = apply_migrations(database_url, os.getenv("SENTINEL_RUNTIME_DB_ROLE") or None)
    print("Applied migrations: " + (", ".join(versions) if versions else "none; schema is current"))


if __name__ == "__main__":
    main()
