import importlib

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tools


def setup_function():
    importlib.reload(tools)  # reset in-memory state between tests


def test_list_records_returns_seed():
    assert len(tools.list_records()) == 3


def test_query_filters_by_plan():
    free = tools.query(plan="free")
    assert {r["user"] for r in free} == {"biscuit", "nibbles"}


def test_delete_records_by_plan_removes_matching():
    result = tools.delete_records(plan="free")
    assert result == {"deleted": 2, "remaining": 1}
    assert tools.list_records()[0]["user"] == "cappuccino"


def test_delete_all_records():
    result = tools.delete_records()
    assert result["remaining"] == 0


def test_dispatch_routes_by_name():
    fn = tools.dispatch("list_records")
    assert callable(fn)
    assert len(fn()) == 3
