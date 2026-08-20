"""The MCP toolbox: which tool gets called, with which arguments.

No server here. What is worth pinning is the mapping from this agent's four methods onto MCP
tool calls, because the server's arguments are optional and a present-but-null argument is not
the same as an absent one. The transport is the SDK's problem.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db
import mcp_db


class RecordingMcp(mcp_db.McpDatabase):
    """Captures the calls instead of making them."""

    def __init__(self):
        super().__init__("http://mcp.invalid/mcp")
        self.calls = []

    def _call(self, tool, arguments=None):
        self.calls.append((tool, arguments or {}))
        return "[{user=biscuit, plan=free}]"


def test_reads_map_to_their_tools():
    m = RecordingMcp()
    m.list_records()
    m.audit_log()
    assert m.calls == [("list_records", {}), ("audit_log", {"limit": 20})]


def test_optional_arguments_are_omitted_not_nulled():
    m = RecordingMcp()
    m.query()
    m.delete_records()
    assert m.calls == [("query", {}), ("delete_records", {})]


def test_optional_arguments_are_sent_when_given():
    m = RecordingMcp()
    m.query(plan="free")
    m.delete_records(plan="free")
    assert m.calls == [("query", {"plan": "free"}), ("delete_records", {"plan": "free"})]


def test_audit_limit_is_clamped_like_the_sql_path():
    m = RecordingMcp()
    m.audit_log(limit=0)
    m.audit_log(limit=5000)
    assert [args["limit"] for _, args in m.calls] == [1, 200]


def test_result_is_the_servers_text_verbatim():
    # Java's List.toString(), not JSON. Passed through unparsed on purpose: it is the same
    # payload the Java agent receives, so recording it verbatim keeps the comparison fair.
    assert RecordingMcp().list_records() == "[{user=biscuit, plan=free}]"


def test_text_joins_every_text_block():
    class Block:
        def __init__(self, text):
            self.type, self.text = "text", text

    class Result:
        content = [Block("first"), Block("second")]

    assert mcp_db._text(Result()) == "first\nsecond"


def test_from_env_prefers_mcp_over_a_dsn(monkeypatch):
    monkeypatch.setenv(mcp_db.URL_ENV, "http://sre-agents-mcp.db.svc.cluster.local:8086/mcp")
    monkeypatch.setenv(db.DSN_ENV, "postgresql://app_svc@production-db.db.svc.cluster.local:5432/production")
    assert isinstance(db.from_env(), mcp_db.McpDatabase)


def test_from_env_falls_back_to_the_dsn(monkeypatch):
    monkeypatch.delenv(mcp_db.URL_ENV, raising=False)
    monkeypatch.setenv(db.DSN_ENV, "postgresql://app_svc@production-db.db.svc.cluster.local:5432/production")
    assert isinstance(db.from_env(), db.PostgresDatabase)


def test_record_count_is_none_when_the_database_answers_in_text():
    """The MCP path returns the server's reply verbatim, so there are no rows to count.

    Regression test for a count that was `len()` of that string: on the MCP path — the one
    the cluster actually runs — five records were reported as 408, the character count of
    the Java `List.toString()` the server sends back. It read like a plausible number, and
    every test passed because the in-memory database returns a real list.
    """
    import tools
    tools.use(RecordingMcp())
    assert tools.record_count() is None

    tools.use(db.InMemoryDatabase(staged=False))
    assert tools.record_count() == 5
