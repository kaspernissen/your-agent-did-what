"""An in-memory fake 'database' the demo agent operates on.

State is module-level so a single agent run mutates it; reload the module to reset.
"""

_SEED = [
    {"id": 1, "user": "alice", "plan": "pro"},
    {"id": 2, "user": "bob", "plan": "free"},
    {"id": 3, "user": "carol", "plan": "free"},
]

_RECORDS = [dict(r) for r in _SEED]


def list_records():
    """Return all records."""
    return [dict(r) for r in _RECORDS]


def query(plan=None):
    """Return records, optionally filtered by plan."""
    if plan is None:
        return list_records()
    return [dict(r) for r in _RECORDS if r["plan"] == plan]


def delete_records(plan=None):
    """Delete records (all, or matching plan). Returns counts. Destructive."""
    global _RECORDS
    before = len(_RECORDS)
    if plan is None:
        _RECORDS = []
    else:
        _RECORDS = [r for r in _RECORDS if r["plan"] != plan]
    return {"deleted": before - len(_RECORDS), "remaining": len(_RECORDS)}


# Anthropic tool-use schemas
TOOL_SCHEMAS = [
    {
        "name": "list_records",
        "description": "List all records in the database.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "query",
        "description": "Query records, optionally filtered by plan (e.g. 'free' or 'pro').",
        "input_schema": {
            "type": "object",
            "properties": {"plan": {"type": "string"}},
        },
    },
    {
        "name": "delete_records",
        "description": "Delete records. With no plan, deletes ALL records. Destructive.",
        "input_schema": {
            "type": "object",
            "properties": {"plan": {"type": "string"}},
        },
    },
]

_DISPATCH = {
    "list_records": list_records,
    "query": query,
    "delete_records": delete_records,
}


def dispatch(name):
    """Return the callable for a tool name."""
    return _DISPATCH[name]
