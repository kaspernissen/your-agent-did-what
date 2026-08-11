"""The capybara customer database — in-memory, mutated by a single agent run.

State is module-level so a single agent run mutates it; reload the module to reset.
"""

# The same roster demo 1 seeds into Postgres, so both demos talk about the same
# capybaras. The scenarios differ — demo 1 is the rogue-service incident, this is the
# convention swap — but the data should not.
_SEED = [
    {"id": 1, "user": "cappuccino", "plan": "pro"},
    {"id": 2, "user": "biscuit", "plan": "free"},
    {"id": 3, "user": "nibbles", "plan": "free"},
    {"id": 4, "user": "mochi", "plan": "pro"},
    {"id": 5, "user": "pepper", "plan": "free"},
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
