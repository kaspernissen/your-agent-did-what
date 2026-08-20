"""The same four tools, reached over MCP instead of over psycopg.

Why this exists: with `PostgresDatabase`, Beaver and Otter hold the toolbox as local Python
functions, while Capybara discovers its toolbox from `customer-db-mcp` and executes it in
another process. That difference confounds any comparison of their *tool* spans, because the
one agent whose tool body runs across a process boundary is also the only one built on a
framework. Pointing the Python agents at the same MCP server removes the variable: all three
then call the same tools, in the same other process, and differ only in what emits the
telemetry.

The result is whatever the server sent back. `CustomerDbTools` returns Java's
`List.toString()`, so it arrives as text like `[{user=biscuit, plan=free}]` rather than JSON.
That is deliberately not parsed here: it is the same payload the Java agent receives over the
same transport, so recording it verbatim is what makes the comparison fair. Whether it lands
on a span is a question about the instrumentation, not about the data being available.

One session per call, mirroring `PostgresDatabase`'s connection per call. A real client would
hold the session open across a conversation; per call keeps the failure modes obvious and the
handshake visible in the trace.

Nothing here propagates trace context, because the SDK already does. mcp 2.x ships its own
instrumentation: `mcp/shared/_otel.py` exposes `inject_trace_context`, which writes W3C
traceparent into the request's `_meta` map, and `extract_trace_context` on the receiving side.
That is the mechanism the GenAI MCP convention prescribes and the one MCP's SEP-414 reserves the
unprefixed keys for, and it is the only propagation that survives a transport which multiplexes
several MCP messages onto one HTTP request. The server agrees: quarkus-mcp-server with tracing
enabled reads `traceparent` out of the same envelope, so the trace joins across the boundary
without either side doing anything special.
"""
from __future__ import annotations

import asyncio

URL_ENV = "CUSTOMER_DB_MCP_URL"

# Streamable HTTP, the transport MCP's 2025-03-26 revision introduced and quarkus-mcp-server
# serves at its root path. The older SSE transport is still mounted at <root>/sse; nothing
# here depends on which one the Java agent picked.
DEFAULT_URL = "http://customer-db-mcp:8086/mcp"


def _text(result) -> str:
    """The text content blocks of a tool result, joined.

    MCP tool results are a list of content blocks. These tools return a single text block;
    joining rather than indexing means a server that splits its answer still works.
    """
    parts = [
        block.text
        for block in getattr(result, "content", []) or []
        if getattr(block, "type", None) == "text"
    ]
    return "\n".join(parts)


class McpDatabase:
    """Capybara's MCP server, called as a database.

    Deliberately the same four methods as `PostgresDatabase`, so `tools.py` and the agent loop
    cannot tell which one they are talking to.
    """

    def __init__(self, url: str):
        self._url = url

    def __repr__(self) -> str:  # shows up in the service's own /health output
        return f"McpDatabase({self._url})"

    def _call(self, tool: str, arguments: dict | None = None):
        """Run one tool call to completion on its own event loop.

        The MCP SDK is async and the agent loop is not, so each call gets an event loop of its
        own. Fine for one tool call at a time, which is what an agent turn does anyway.
        """
        return asyncio.run(self._call_async(tool, arguments or {}))

    async def _call_async(self, tool: str, arguments: dict):
        # mcp 2.x: streamable_http_client yields two streams, not three, and talks httpx2 rather
        # than httpx, so the httpx instrumentation this agent installs never sees it. The SDK
        # traces and propagates for itself, which is why that costs us nothing.
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with streamable_http_client(self._url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
                if getattr(result, "isError", False):
                    raise RuntimeError(f"MCP tool {tool} failed: {_text(result)}")
                return _text(result)

    # The toolbox. Arguments are omitted rather than sent as null, because the server's
    # @ToolArg parameters are optional and a present-but-null argument is not the same thing.
    def list_records(self):
        return self._call("list_records")

    def query(self, plan=None):
        return self._call("query", {"plan": plan} if plan else {})

    def audit_log(self, limit=20):
        return self._call("audit_log", {"limit": max(1, min(int(limit), 200))})

    def delete_records(self, plan=None):
        return self._call("delete_records", {"plan": plan} if plan else {})
