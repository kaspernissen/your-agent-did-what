"""The capybara customer database — in-memory, mutated by a single agent run.

Deliberately the same story as demo 1: the same five capybaras, the same rogue
neighbouring service, the same audit trail that makes the deletion attributable, and
the same question put to the agent. Only one thing differs between the two demos, and
it is the instrumentation library — which is the whole point. If the scenarios differed
too, nothing the audience saw could be attributed to the convention.

What is NOT the same is the depth: demo 1 has real Postgres roles, a SECURITY DEFINER
trigger and grants you can inspect. Here the audit trail is a list of dicts. It exists
to give the agent something honest to find, not to teach anyone about Postgres.

State is module-level so a single agent run mutates it; reload the module to reset.
"""

# The same roster demo 1 seeds into Postgres, so both demos talk about the same
# capybaras.
_SEED = [
    {"id": 1, "user": "cappuccino", "plan": "pro"},
    {"id": 2, "user": "biscuit", "plan": "free"},
    {"id": 3, "user": "nibbles", "plan": "free"},
    {"id": 4, "user": "mochi", "plan": "pro"},
    {"id": 5, "user": "pepper", "plan": "free"},
]

_RECORDS = [dict(r) for r in _SEED]

# Who touched what. Demo 1 gets this from a Postgres trigger, which is why it can be
# trusted there; here it is simply recorded alongside the deletion. Two fields rather
# than one, because the distinction is the demo's: `client` is self-reported and any
# connection can claim anything, while `db_user` is the authenticated role.
_AUDIT: list[dict] = []


def simulate_incident():
    """The kangaroos go rogue: delete every free-plan capybara, and leave a trail.

    The mirror of demo 1's POST /incident/kangaroo. Called before the agent runs, so
    the state it investigates was produced by something other than itself — an agent
    that caused the incident it is diagnosing proves nothing.
    """
    global _RECORDS
    doomed = [r for r in _RECORDS if r["plan"] == "free"]
    _RECORDS = [r for r in _RECORDS if r["plan"] != "free"]
    for r in doomed:
        _AUDIT.append({
            "operation": "DELETE",
            "user": r["user"],
            "plan": r["plan"],
            "client": "kangaroo-service",
            "db_user": "kangaroo",
        })
    return {"deleted": len(doomed), "remaining": len(_RECORDS)}


def audit_log(limit=20):
    """Return the most recent changes. This is the tool that answers 'who did this?'."""
    return [dict(e) for e in _AUDIT[-max(1, min(limit, 200)):]]


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
        "name": "audit_log",
        "description": (
            "Recent changes to the database: what happened, and which client and "
            "database role did it. Use this to find out who changed something."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
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
    "audit_log": audit_log,
    "delete_records": delete_records,
}


def dispatch(name):
    """Return the callable for a tool name."""
    return _DISPATCH[name]
