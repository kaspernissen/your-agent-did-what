"""An HTTP front for the agent, so a run can be triggered without a rebuild.

Why a service rather than the CLI: it stays up, so asking a question costs one request
instead of a container start. The capybara-sre console calls this endpoint.

The instrumentation library is installed once, at import. There is nothing to switch:
this image ships exactly one of the two libraries, which is what keeps the comparison
with the sibling agent honest.

    POST /run     {"prompt": "..."}  ->  the answer, the tool calls, and the trace id
    GET  /healthz

stdlib only: two endpoints do not justify a web framework, and every dependency here has
to be installed into the image.
"""
from __future__ import annotations

import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import telemetry
import tools
from agent import SreAgent

DEFAULT_PROMPT = "Customers are reporting missing accounts. Investigate what happened."
PORT = int(os.environ.get("PORT", "8000"))

# Installed once, at import. See the module docstring for why this cannot be per-request.
AGENT_NAME = os.environ.get("AGENT_NAME", "db-ops-agent")
CONVENTION = telemetry.CONVENTION
TRACER = telemetry.configure(AGENT_NAME)


def investigate(prompt: str) -> dict:
    """Run one investigation against whatever state the database is in.

    Nothing is staged or reset here. This agent reads the same database Capybara does, so
    the incident is whatever actually happened — triggered from Capybara's console, by a
    coding agent borrowing the deploy_svc role. An agent that set up its own incident
    would be reporting on itself.

    A fresh agent per call: the trace id and tool calls it records are per-run state, and
    sharing one agent across concurrent requests would interleave them.
    """
    agent = SreAgent(TRACER, name=AGENT_NAME)
    answer = agent.run(prompt)

    return {
        "convention": CONVENTION,
        "agentName": AGENT_NAME,
        "model": agent.model,
        "prompt": prompt,
        # None on the MCP path, which returns text rather than rows. See tools.record_count.
        "records": tools.record_count(),
        "answer": answer,
        "toolCalls": agent.tool_calls,
        "traceId": agent.trace_id,
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path.rstrip("/") in ("/healthz", ""):
            self._json(200, {"status": "ok", "convention": CONVENTION, "agent": AGENT_NAME})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/run":
            self._json(404, {"error": "not found"})
            return
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            payload = json.loads(body) if body else {}
            prompt = (payload.get("prompt") or "").strip() or DEFAULT_PROMPT
            self._json(200, investigate(prompt))
        except Exception as exc:                       # noqa: BLE001 - report, never crash
            traceback.print_exc()
            self._json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        # The console is served from another origin, so the browser needs this to be
        # allowed to read the response at all.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        """One line per request on stdout, so kubectl logs stays readable."""
        print(f"{self.address_string()} {fmt % args}", flush=True)


def main() -> None:
    print(f"convention   {CONVENTION}", flush=True)
    print(f"agent        {AGENT_NAME}", flush=True)
    print(f"collector    {telemetry.endpoint()}", flush=True)
    print(f"listening    0.0.0.0:{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
