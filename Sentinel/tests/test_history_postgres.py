"""Integration tests use only an explicitly supplied disposable *_test database."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import subprocess
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from sentinel import history
from sentinel.history import (
    HistoryError,
    _connection,
    compare_history,
    get_report,
    import_comparison,
    import_suite,
    migrate,
    query_history,
)
from sentinel.history_cli import main
from tests.history_fixtures import history_report

pytestmark = pytest.mark.postgres


@dataclass
class Database:
    owner: str = field(repr=False)
    writer: str = field(repr=False)
    reader: str = field(repr=False)


@pytest.fixture(scope="module")
def database_roles() -> Iterator[Database]:
    dsn = os.environ.get("SENTINEL_HISTORY_TEST_DSN")
    if not dsn:
        pytest.skip("set SENTINEL_HISTORY_TEST_DSN to a disposable PostgreSQL database")
    options = conninfo_to_dict(dsn)
    if not options.get("dbname", "").endswith("_test"):
        pytest.fail("integration database name must end in _test")
    migrate(dsn)
    names = ["history_reader_" + secrets.token_hex(5), "history_writer_" + secrets.token_hex(5)]
    passwords = [secrets.token_hex(20), secrets.token_hex(20)]
    with psycopg.connect(dsn) as conn:
        conn.execute((Path(__file__).parents[1] / "history/roles.sql").read_text())
        for name, password, group in zip(
            names,
            passwords,
            ["sentinel_history_reader", "sentinel_history_writer"],
            strict=True,
        ):
            conn.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(name),
                    sql.Literal(password),
                )
            )
            conn.execute(
                sql.SQL("GRANT {} TO {}").format(sql.Identifier(group), sql.Identifier(name))
            )
    yield Database(
        owner=dsn,
        reader=make_conninfo(dsn, user=names[0], password=passwords[0]),
        writer=make_conninfo(dsn, user=names[1], password=passwords[1]),
    )
    with psycopg.connect(dsn) as conn:
        for name in names:
            conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(name)))


@pytest.fixture
def database(database_roles: Database) -> Database:
    with psycopg.connect(database_roles.owner) as conn:
        conn.execute("DROP SCHEMA sentinel_history CASCADE")
    migrate(database_roles.owner)
    with psycopg.connect(database_roles.owner) as conn:
        conn.execute((Path(__file__).parents[1] / "history/roles.sql").read_text())
    return database_roles


def ingest(database: Database, release: str = "v1", *, unsafe: bool = False) -> str:
    return str(
        import_suite(
            database.writer,
            history_report(unsafe=unsafe, cost=0.02 if unsafe else 0.01).model_dump_json().encode(),
            suite="demo",
            release=release,
        )["id"]
    )


def test_idempotent_and_concurrent_import(database: Database) -> None:
    raw = history_report().model_dump_json().encode()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(
                lambda _: import_suite(database.writer, raw, suite="demo", release="v1"),
                range(4),
            )
        )
    assert sum(result["inserted"] for result in results) == 1
    assert len({result["id"] for result in results}) == 1
    formatted = json.dumps(json.loads(raw), indent=4).encode()
    assert not import_suite(database.writer, formatted, suite="demo", release="v1")["inserted"]
    assert len(query_history(database.reader, suite="demo")["items"]) == 1
    stored = get_report(database.reader, results[0]["id"])
    assert stored["source_sha256"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(HistoryError, match="different report"):
        ingest(database, unsafe=True)


def test_partial_import_rolls_back(database: Database) -> None:
    with psycopg.connect(database.owner) as conn:
        conn.execute("REVOKE INSERT ON sentinel_history.tags FROM sentinel_history_writer")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        ingest(database)
    assert query_history(database.reader, suite="demo")["items"] == []
    with psycopg.connect(database.owner) as conn:
        assert conn.execute("SELECT count(*) FROM sentinel_history.runs").fetchone() == (0,)


def test_roles_enforce_read_only_and_append_only(database: Database) -> None:
    report_id = ingest(database)
    assert get_report(database.reader, report_id)["release"] == "v1"
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        import_suite(
            database.reader,
            history_report().model_dump_json().encode(),
            suite="demo",
            release="v2",
        )
    for dsn, statement in [
        (database.reader, "DELETE FROM sentinel_history.suites"),
        (database.writer, "UPDATE sentinel_history.suites SET release='rewritten'"),
        (database.writer, "DELETE FROM sentinel_history.suites"),
        (database.writer, "TRUNCATE sentinel_history.suites CASCADE"),
        (database.writer, "CREATE TABLE sentinel_history.unauthorized (id int)"),
        (
            database.writer,
            "INSERT INTO sentinel_history.schema_migrations VALUES (99, 'bad', now())",
        ),
    ]:
        with psycopg.connect(dsn) as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(statement)
            conn.rollback()
    with _connection(database.writer) as conn, pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        conn.execute("INSERT INTO sentinel_history.cases VALUES (%s, 'another')", (report_id,))
        conn.rollback()


def test_queries_and_release_replay(database: Database) -> None:
    first = ingest(database)
    second = ingest(database, "v2", unsafe=True)
    page = query_history(database.reader, suite="demo", limit=1)
    assert page["items"][0]["id"] == first
    assert page["next_offset"] == 1
    assert query_history(database.reader, suite="demo", offset=1)["items"][0]["id"] == second
    failures = query_history(
        database.reader,
        suite="demo",
        view="runs",
        case_id="privacy",
        tag="security",
        safety_only=True,
    )["items"]
    assert len(failures) == 1 and failures[0]["suite_id"] == second
    slices = query_history(database.reader, suite="demo", view="slices", tag="security")["items"]
    assert len(slices) == 2 and slices[1]["safety_pass_rate"] == 0
    replay = compare_history(database.reader, first, second)
    assert replay["cost_delta_usd"] == pytest.approx(0.01)
    assert replay["comparison"]["promotion_recommended"] is False
    assert replay["comparison"]["regressions"][0]["reason"] == "safety regression"
    raw = json.dumps(replay["comparison"]).encode()
    assert import_comparison(database.writer, raw, baseline_id=first, candidate_id=second)[
        "inserted"
    ]
    assert not import_comparison(database.writer, raw, baseline_id=first, candidate_id=second)[
        "inserted"
    ]
    assert len(query_history(database.reader, suite="demo", view="comparisons")["items"]) == 1
    changed = json.loads(raw)
    changed["promotion_recommended"] = True
    with pytest.raises(HistoryError, match="does not match"):
        import_comparison(
            database.writer, json.dumps(changed).encode(), baseline_id=first, candidate_id=second
        )


@pytest.mark.parametrize("changed", ["cases", "config", "run_keys"])
def test_incompatible_reports_cannot_be_compared(database: Database, changed: str) -> None:
    first = ingest(database)
    report = history_report()
    if changed == "cases":
        report.input_hashes["cases"] = "d" * 64
    elif changed == "config":
        report.config.run_min_score = 0.7
    else:
        report.results[0].run_id = "different-trial"
    second = import_suite(
        database.writer, report.model_dump_json().encode(), suite="demo", release="v2"
    )
    with pytest.raises(HistoryError, match="same suite"):
        compare_history(database.reader, first, second["id"])


def test_owner_retention_cascades_comparisons(database: Database) -> None:
    first, second = ingest(database), ingest(database, "v2", unsafe=True)
    raw = json.dumps(compare_history(database.reader, first, second)["comparison"]).encode()
    import_comparison(database.writer, raw, baseline_id=first, candidate_id=second)
    with psycopg.connect(database.owner) as conn:
        conn.execute("DELETE FROM sentinel_history.suites WHERE id=%s", (first,))
    assert query_history(database.reader, suite="demo", view="comparisons")["items"] == []
    assert get_report(database.reader, second)["release"] == "v2"
    with psycopg.connect(database.owner) as conn:
        assert conn.execute("SELECT count(*) FROM sentinel_history.regressions").fetchone() == (0,)
        assert conn.execute("SELECT count(*) FROM sentinel_history.runs").fetchone() == (1,)


def test_failed_migration_rolls_back_all_ddl(
    database: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(database.owner) as conn:
        conn.execute("DROP SCHEMA sentinel_history CASCADE")
    shutil.copytree(Path(history.__file__).parent / "migrations", tmp_path / "migrations")
    broken = tmp_path / "migrations/002_history_indexes.sql"
    broken.write_text(broken.read_text() + "\nSELECT 1/0;\n")
    monkeypatch.setattr(history, "files", lambda _: tmp_path)
    with pytest.raises(psycopg.errors.DivisionByZero):
        migrate(database.owner)
    with psycopg.connect(database.owner) as conn:
        assert conn.execute("SELECT to_regnamespace('sentinel_history')").fetchone() == (None,)


def test_forward_upgrade_checksum_and_no_downgrade(database: Database) -> None:
    with psycopg.connect(database.owner) as conn:
        conn.execute("DROP SCHEMA sentinel_history CASCADE")
    assert migrate(database.owner, target=1) == 1
    with psycopg.connect(database.owner) as conn:
        conn.execute((Path(__file__).parents[1] / "history/roles.sql").read_text())
    report_id = ingest(database)
    assert migrate(database.owner) == 2
    assert migrate(database.owner) == 2
    assert get_report(database.reader, report_id)["release"] == "v1"
    with pytest.raises(HistoryError, match="downgrades"):
        migrate(database.owner, target=1)
    with psycopg.connect(database.owner) as conn:
        conn.execute(
            "UPDATE sentinel_history.schema_migrations SET sha256='changed' WHERE version=1"
        )
    with pytest.raises(HistoryError, match="checksum"):
        migrate(database.owner)


def test_cli_import_and_query(
    database: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SENTINEL_HISTORY_WRITER_DSN", database.writer)
    monkeypatch.setenv("SENTINEL_HISTORY_READER_DSN", database.reader)
    source = tmp_path / "suite.json"
    source.write_text(history_report().model_dump_json())
    assert main(["import-suite", "--input", str(source), "--suite", "demo", "--release", "v1"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["inserted"] is True
    assert main(["get", "--id", result["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["report"]["gate_passed"] is True
    assert main(["query", "--suite", "demo"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1


def test_backup_restore_reproduces_comparison(database: Database, tmp_path: Path) -> None:
    if not shutil.which("pg_dump") or not shutil.which("pg_restore"):
        pytest.fail("PostgreSQL integration tests require pg_dump and pg_restore")
    first, second = ingest(database), ingest(database, "v2", unsafe=True)
    before = compare_history(database.reader, first, second)
    raw = json.dumps(before["comparison"]).encode()
    import_comparison(database.writer, raw, baseline_id=first, candidate_id=second)
    backup = tmp_path / "history.dump"
    env = os.environ.copy()
    for key, value in conninfo_to_dict(database.owner).items():
        env[{"dbname": "PGDATABASE"}.get(key, "PG" + key.upper())] = value
    subprocess.run(
        ["pg_dump", "--no-owner", "--no-privileges", "-Fc", "-f", str(backup)],
        env=env,
        check=True,
        capture_output=True,
    )
    restore_name = "sentinel_restore_" + secrets.token_hex(5) + "_test"
    with psycopg.connect(database.owner, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(restore_name)))
    try:
        env["PGDATABASE"] = restore_name
        subprocess.run(
            [
                "pg_restore",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                restore_name,
                str(backup),
            ],
            env=env,
            check=True,
            capture_output=True,
        )
        restored = make_conninfo(database.owner, dbname=restore_name)
        assert migrate(restored) == 2
        with psycopg.connect(restored) as conn:
            conn.execute((Path(__file__).parents[1] / "history/roles.sql").read_text())
        restored_reader = make_conninfo(database.reader, dbname=restore_name)
        restored_writer = make_conninfo(database.writer, dbname=restore_name)
        assert compare_history(restored_reader, first, second) == before
        assert len(query_history(restored_reader, suite="demo", view="comparisons")["items"]) == 1
        assert not import_suite(
            restored_writer, history_report().model_dump_json().encode(), suite="demo", release="v1"
        )["inserted"]
    finally:
        with psycopg.connect(database.owner, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(restore_name)))
