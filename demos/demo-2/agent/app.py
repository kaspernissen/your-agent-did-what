"""CLI entry point: wire telemetry to the agent and run one incident.

    ./run.sh
    CAPYBARA_INSTRUMENTATION=openinference ./run.sh "…"

Kept deliberately thin. Everything worth reading is in `agent.py` (the loop),
`telemetry.py` (which convention) and `tools.py` (the database).
"""
from __future__ import annotations

import os
import sys

import telemetry
import tools
from agent import DEFAULT_AGENT_NAME, CapybaraAgent

# The same question demo 1's console puts to Capybara SRE, word for word. Two demos,
# one scenario, so the only thing that differs on screen is the vocabulary.
DEFAULT_PROMPT = "Customers are reporting missing accounts. Investigate what happened."


def main(argv: list[str]) -> int:
    prompt = " ".join(argv[1:]) or DEFAULT_PROMPT
    convention = telemetry.selected()

    # The incident happens before the agent is asked about it, and not by the agent.
    incident = tools.simulate_incident()
    tracer = telemetry.configure(os.environ.get("CAPYBARA_AGENT_NAME", DEFAULT_AGENT_NAME))
    agent = CapybaraAgent(tracer, name=os.environ.get("CAPYBARA_AGENT_NAME", DEFAULT_AGENT_NAME))

    print(f"\ninstrumentation  {convention}")
    print(f"model            {agent.model}")
    print(f"collector        {telemetry.endpoint()}")
    print(f"incident         kangaroo-service deleted {incident['deleted']} "
          f"free-plan capybaras, {incident['remaining']} left")
    print(f"\n>>> {prompt}\n")
    try:
        print(agent.run(prompt))
    finally:
        # Without this the batch processor can exit before exporting.
        telemetry.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
