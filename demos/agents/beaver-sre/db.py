"""Where the capybara records live, for Beaver.

Two implementations behind one small interface:

  PostgresDatabase  the real one, and the same one Capybara reads. Both agents then
                    report on the identical state, so when the kangaroos are unleashed
                    from Capybara's console, Beaver sees exactly that and nothing it
                    invented for itself.

  InMemoryDatabase  for tests, and for running this agent with no cluster at all. It
                    seeds the *aftermath* — the free-plan rows already gone, with a
                    matching audit trail — because standalone there is no kangaroo
                    button to press. That is a fabricated incident and the docstring
                    says so; the Postgres path fabricates nothing.

Connecting as capybara_app, the same role the MCP server uses, because Beaver is another
well-behaved application rather than a privileged one. application_name is beaver-sre, so
if it ever does write, the audit trail names it — and the role still says capybara_app,
which is the distinction the whole demo turns on: the client name is self-reported, the
role is authenticated.
"""
from __future__ import annotations

import os

DSN_ENV = "CAPYBARA_DB_DSN"
APPLICATION_NAME = "beaver-sre"

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
                 "client": "kangaroo-service", "db_user": "kangaroo"}
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
            "SELECT username AS user, plan FROM capybaras ORDER BY created_at, username")

    def query(self, plan=None):
        if plan is None:
            return self.list_records()
        return self._rows(
            "SELECT username AS user, plan FROM capybaras WHERE plan = %s"
            " ORDER BY created_at, username", (plan,))

    def audit_log(self, limit=20):
        return self._rows(
            "SELECT to_char(happened_at, 'HH24:MI:SS') AS at, operation,"
            "       username AS user, plan, client, db_user"
            " FROM audit_log ORDER BY id DESC LIMIT %s",
            (max(1, min(int(limit), 200)),))

    def delete_records(self, plan=None):
        sql = "DELETE FROM capybaras" if plan is None else "DELETE FROM capybaras WHERE plan = %s"
        params = () if plan is None else (plan,)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            deleted = cur.rowcount
            cur.execute("SELECT count(*) FROM capybaras")
            remaining = cur.fetchone()[0]
        return {"deleted": deleted, "remaining": remaining}


def from_env():
    """Postgres when a DSN is configured, otherwise the hermetic stand-in."""
    dsn = os.environ.get(DSN_ENV, "").strip()
    return PostgresDatabase(dsn) if dsn else InMemoryDatabase()
