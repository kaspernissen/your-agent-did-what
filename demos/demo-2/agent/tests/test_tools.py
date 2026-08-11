import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db
import tools

FREE, PRO = 3, 2   # biscuit, nibbles, pepper · cappuccino, mochi


def setup_function():
    # Unstaged: the full roster, empty trail. Tests that want the aftermath say so.
    tools.use(db.InMemoryDatabase(staged=False))


def test_list_records_returns_the_roster():
    assert len(tools.list_records()) == FREE + PRO


def test_query_filters_by_plan():
    assert {r["user"] for r in tools.query(plan="free")} == {"biscuit", "nibbles", "pepper"}


def test_delete_records_by_plan_removes_matching():
    assert tools.delete_records(plan="free") == {"deleted": FREE, "remaining": PRO}
    assert {r["plan"] for r in tools.list_records()} == {"pro"}


def test_delete_all_records():
    assert tools.delete_records()["remaining"] == 0


def test_audit_log_is_empty_when_nothing_has_happened():
    assert tools.audit_log() == []


def test_staged_database_shows_the_aftermath_and_who_caused_it():
    """The in-memory default stands in for the state Postgres would be in mid-demo."""
    tools.use(db.InMemoryDatabase())
    assert {r["plan"] for r in tools.list_records()} == {"pro"}

    trail = tools.audit_log()
    assert len(trail) == FREE
    # The two qualities of evidence: the client is self-reported, the role is authenticated.
    assert {e["client"] for e in trail} == {"kangaroo-service"}
    assert {e["db_user"] for e in trail} == {"kangaroo"}


def test_audit_log_respects_its_limit():
    tools.use(db.InMemoryDatabase())
    assert len(tools.audit_log(limit=2)) == 2


def test_every_advertised_tool_is_dispatchable():
    """A schema the model can call but dispatch cannot route is a runtime KeyError."""
    for schema in tools.TOOL_SCHEMAS:
        assert callable(tools.dispatch(schema["name"])), schema["name"]


def test_from_env_picks_postgres_only_when_a_dsn_is_set(monkeypatch):
    monkeypatch.delenv(db.DSN_ENV, raising=False)
    assert isinstance(db.from_env(), db.InMemoryDatabase)
    monkeypatch.setenv(db.DSN_ENV, "postgresql://x/y")
    assert isinstance(db.from_env(), db.PostgresDatabase)
