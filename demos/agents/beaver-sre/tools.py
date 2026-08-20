"""The tools the agent can call, and the schemas the model sees.

Deliberately thin: every function delegates to whichever database `db.py` selected, so
this module describes the *toolbox* and nothing about storage. The agent loop
(`agent.py`) knows about neither.

This agent does not stage its own incident. The state comes from the shared database, so
the deletion goose makes through goose-mcp is the same event the agent reports on — which is
the point of pointing them all at one database.
"""
from __future__ import annotations

import db

_DB = db.from_env()


def use(database) -> None:
    """Swap the database. Tests use this; nothing else should need it."""
    global _DB
    _DB = database


def list_records():
    """All customer records."""
    return _DB.list_records()


def query(plan=None):
    """Records, optionally filtered by plan."""
    return _DB.query(plan)


def audit_log(limit=20):
    """Recent changes, with the client and database role behind each one."""
    return _DB.audit_log(limit)


def delete_records(plan=None):
    """Delete records (all, or matching plan). Destructive."""
    return _DB.delete_records(plan)


def record_count():
    """How many records are in the database, or None when that cannot be known honestly.

    The MCP path returns the server's reply as text and mcp_db.py deliberately does not
    parse it, so there is no list to measure. `len()` on that string would report its
    character count — a number that looks like a record count and is not. Callers say
    "unknown" instead.
    """
    records = _DB.list_records()
    return len(records) if isinstance(records, list) else None


# Anthropic tool-use schemas.
TOOL_SCHEMAS = [
    {
        "name": "list_records",
        "description": "List all customer records in the database.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "query",
        "description": "Query records, optionally filtered by plan (e.g. 'free' or 'pro').",
        "input_schema": {"type": "object", "properties": {"plan": {"type": "string"}}},
    },
    {
        "name": "audit_log",
        "description": (
            "Recent changes to the customer table: what happened, and which client and "
            "database role did it. Use this to find out who changed something."
        ),
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}}},
    },
    {
        "name": "delete_records",
        "description": "Delete records. With no plan, deletes ALL records. Destructive.",
        "input_schema": {"type": "object", "properties": {"plan": {"type": "string"}}},
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
