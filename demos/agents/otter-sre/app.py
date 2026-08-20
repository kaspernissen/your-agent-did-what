"""CLI entry point: wire telemetry to the agent and run one incident.

    ./run.sh
    ./run.sh "Customers are reporting missing accounts. Investigate."

Kept deliberately thin. Everything worth reading is in `agent.py` (the loop),
`telemetry.py` (which convention) and `tools.py` (the database).
"""
from __future__ import annotations

import os
import sys

import telemetry
import tools
from agent import DEFAULT_AGENT_NAME, SreAgent

# The same question the console sends, so a CLI run and a console run are comparable.
DEFAULT_PROMPT = "Customers are reporting missing accounts. Investigate what happened."


def main(argv: list[str]) -> int:
    prompt = " ".join(argv[1:]) or DEFAULT_PROMPT
    convention = telemetry.CONVENTION

    tracer = telemetry.configure(os.environ.get("AGENT_NAME", DEFAULT_AGENT_NAME))
    agent = SreAgent(tracer, name=os.environ.get("AGENT_NAME", DEFAULT_AGENT_NAME))

    print(f"\ninstrumentation  {convention}")
    print(f"model            {agent.model}")
    print(f"collector        {telemetry.endpoint()}")
    count = tools.record_count()
    print(f"records          {count} in the database" if count is not None
          else "records          not counted (the MCP path returns text; see mcp_db.py)")
    print(f"\n>>> {prompt}\n")
    try:
        print(agent.run(prompt))
    finally:
        # Without this the batch processor can exit before exporting.
        telemetry.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
