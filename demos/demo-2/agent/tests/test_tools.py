import importlib

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tools


def setup_function():
    importlib.reload(tools)  # reset in-memory state between tests


FREE, PRO = 3, 2   # biscuit, nibbles, pepper · cappuccino, mochi


def test_list_records_returns_seed():
    assert len(tools.list_records()) == FREE + PRO


def test_query_filters_by_plan():
    free = tools.query(plan="free")
    assert {r["user"] for r in free} == {"biscuit", "nibbles", "pepper"}


def test_delete_records_by_plan_removes_matching():
    result = tools.delete_records(plan="free")
    assert result == {"deleted": FREE, "remaining": PRO}
    assert tools.list_records()[0]["user"] == "cappuccino"


def test_delete_all_records():
    result = tools.delete_records()
    assert result["remaining"] == 0


def test_audit_log_is_empty_until_something_happens():
    assert tools.audit_log() == []


def test_simulate_incident_deletes_free_and_records_who():
    result = tools.simulate_incident()
    assert result == {"deleted": FREE, "remaining": PRO}
    assert {r["plan"] for r in tools.list_records()} == {"pro"}

    trail = tools.audit_log()
    assert len(trail) == FREE
    # The two qualities of evidence, which is the point the trail exists to make:
    # the client is self-reported, the database role is authenticated.
    assert {e["client"] for e in trail} == {"kangaroo-service"}
    assert {e["db_user"] for e in trail} == {"kangaroo"}
    assert {e["operation"] for e in trail} == {"DELETE"}


def test_audit_log_respects_its_limit():
    tools.simulate_incident()
    assert len(tools.audit_log(limit=2)) == 2


def test_dispatch_routes_by_name():
    fn = tools.dispatch("list_records")
    assert callable(fn)
    assert len(fn()) == FREE + PRO


def test_every_advertised_tool_is_dispatchable():
    """A schema the model can call but dispatch cannot route is a runtime KeyError."""
    for schema in tools.TOOL_SCHEMAS:
        assert callable(tools.dispatch(schema["name"])), schema["name"]
