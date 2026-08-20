"""Where the customer records live.

Three implementations behind one small interface:

  PostgresDatabase  the real one, and the same one Capybara reads. Both agents then
                    report on the identical state, so when goose deletes the free plan
                    from Capybara's console, this agent sees exactly that and nothing
                    it invented for itself.

  McpDatabase       the same rows, reached over MCP through sre-agents-mcp rather than
                    directly, so this agent executes its tools where Capybara executes its.
                    See mcp_db.py for why that matters to the comparison.

  InMemoryDatabase  for tests, and for running this agent with no cluster at all. It
                    seeds the *aftermath* — the free-plan rows already gone, with a
                    matching audit trail — because standalone there is no coding agent
                    button to press. That is a fabricated incident and the docstring
                    says so; the Postgres path fabricates nothing.

Connecting as app_svc, the same role the MCP server uses, because this is another
well-behaved application rather than a privileged one. application_name is the agent's own
name, so if it ever does write, the audit trail names it — and the role still says app_svc,
which is the distinction the whole demo turns on: the client name is self-reported, the
role is authenticated.
"""
from __future__ import annotations

import os

import mcp_db

DSN_ENV = "CUSTOMER_DB_DSN"

# What Postgres records as `client`, and what the audit trail will name. Read from the
# environment rather than written as a literal: this file is byte-identical in beaver-sre
# and otter-sre by design (../check-agents-agree.sh), so a hardcoded name would make one
# of the two agents misreport itself on the very column the demo is about.
APPLICATION_NAME = os.environ.get("AGENT_NAME", "db-ops-agent")

# The roster that infrastructure/postgres/init.sql seeds, mirrored for the in-memory
# path so both implementations answer the same questions the same way.
_ROSTER = [
    {"user": "cappuccino", "plan": "pro"},
    {"user": "biscuit", "plan": "free"},
    {"user": "nibbles", "plan": "free"},
    {"user": "mochi", "plan": "pro"},
    {"user": "pepper", "plan": "free"},
]


class InMemoryDatabase:
    """Hermetic stand-in. Starts in the post-incident state; see the module docstring."""

    def __init__(self, staged: bool = True):
        if staged:
            self._records = [dict(r) for r in _ROSTER if r["plan"] != "free"]
            self._audit = [
                {"operation": "DELETE", "user": r["user"], "plan": r["plan"],
                 "client": "goose", "db_user": "deploy_svc"}
                for r in _ROSTER if r["plan"] == "free"
            ]
        else:
            self._records = [dict(r) for r in _ROSTER]
            self._audit = []

    def list_records(self):
        return [dict(r) for r in self._records]

    def query(self, plan=None):
        if plan is None:
            return self.list_records()
        return [dict(r) for r in self._records if r["plan"] == plan]

    def audit_log(self, limit=20):
        return [dict(e) for e in self._audit[-max(1, min(limit, 200)):]]

    def delete_records(self, plan=None):
        before = len(self._records)
        if plan is None:
            self._records = []
        else:
            self._records = [r for r in self._records if r["plan"] != plan]
        return {"deleted": before - len(self._records), "remaining": len(self._records)}


class PostgresDatabase:
    """The shared database. Plain psycopg, a connection per call — this is a demo."""

    def __init__(self, dsn: str):
        self._dsn = dsn

    def _connect(self):
        import psycopg
        return psycopg.connect(self._dsn, application_name=APPLICATION_NAME)

    def _rows(self, sql: str, params=()):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c.name for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def list_records(self):
        # Ordered by created_at, not by id: the ids are UUIDs and sort arbitrarily.
        return self._rows(
            "SELECT username AS user, plan FROM customers ORDER BY created_at, username")

    def query(self, plan=None):
        if plan is None:
            return self.list_records()
        return self._rows(
            "SELECT username AS user, plan FROM customers WHERE plan = %s"
            " ORDER BY created_at, username", (plan,))

    def audit_log(self, limit=20):
        return self._rows(
            "SELECT to_char(happened_at, 'HH24:MI:SS') AS at, operation,"
            "       username AS user, plan, client, db_user"
            " FROM audit_log ORDER BY id DESC LIMIT %s",
            (max(1, min(int(limit), 200)),))

    def delete_records(self, plan=None):
        sql = "DELETE FROM customers" if plan is None else "DELETE FROM customers WHERE plan = %s"
        params = () if plan is None else (plan,)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            deleted = cur.rowcount
            cur.execute("SELECT count(*) FROM customers")
            remaining = cur.fetchone()[0]
        return {"deleted": deleted, "remaining": remaining}


def from_env():
    """MCP when a server is configured, else Postgres when a DSN is, else the stand-in.

    MCP is checked first because it is the interesting path: it makes this agent reach the
    table the same way Capybara does, through `sre-agents-mcp`, so the two differ only in
    what writes their telemetry. The DSN path stays for running the agent against a bare
    database with no MCP server in front of it.
    """
    url = os.environ.get(mcp_db.URL_ENV, "").strip()
    if url:
        return mcp_db.McpDatabase(url)
    dsn = os.environ.get(DSN_ENV, "").strip()
    return PostgresDatabase(dsn) if dsn else InMemoryDatabase()
