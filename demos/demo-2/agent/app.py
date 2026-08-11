"""CLI entry point: wire telemetry to the agent and run one incident.

    ./run.sh "We are over quota. Delete the free-plan capybaras."
    CAPYBARA_INSTRUMENTATION=openinference ./run.sh "…"

Kept deliberately thin. Everything worth reading is in `agent.py` (the loop),
`telemetry.py` (which convention) and `tools.py` (the database).
"""
from __future__ import annotations

import sys

import telemetry
from agent import DEFAULT_AGENT_NAME, CapybaraAgent

DEFAULT_PROMPT = "List all the records in the database."


def main(argv: list[str]) -> int:
    prompt = " ".join(argv[1:]) or DEFAULT_PROMPT
    convention = telemetry.selected()
    tracer = telemetry.configure(DEFAULT_AGENT_NAME)
    agent = CapybaraAgent(tracer, name=DEFAULT_AGENT_NAME)

    print(f"\ninstrumentation  {convention}")
    print(f"model            {agent.model}")
    print(f"collector        {telemetry.endpoint()}")
    print(f"\n>>> {prompt}\n")
    try:
        print(agent.run(prompt))
    finally:
        # Without this the batch processor can exit before exporting.
        telemetry.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
