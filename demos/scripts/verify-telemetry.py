#!/usr/bin/env python3
"""Assert that the telemetry this stack is configured to emit actually arrived.

Enabling the tool-call content and confirming it reached the collector are different jobs,
and only the first is a config change. This is the second, made executable: it reads the
collector's debug output and checks three things:

  1. CORE CONVENTIONS — the attributes a conforming run must produce. Missing any
     of these is a broken setup and exits non-zero.
  2. FORENSIC CONTENT — gen_ai.tool.call.arguments / .result. Whether these are
     expected depends on which tool path ran, so the script takes the path and
     checks the result against it rather than assuming.
  3. EVALUATIONS — gen_ai.evaluation.result events from the judge.

Usage
  ./scripts/verify-telemetry.py                # the in-cluster collector, path from $AGENT_TOOLS
  ./scripts/verify-telemetry.py --path local   # override the expected path
  ./scripts/verify-telemetry.py run.log        # read a file
  kubectl logs -n observability -l app.kubernetes.io/name=opentelemetry-collector \
    | ./scripts/verify-telemetry.py -          # or a pipe
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

CORE = [
    ("invoke_agent span", r"invoke_agent"),
    ("chat span", r"\bchat\b"),
    ("execute_tool span", r"execute_tool|tools/call"),
    ("gen_ai.operation.name", r"gen_ai\.operation\.name"),
    ("gen_ai.provider.name", r"gen_ai\.provider\.name"),
    ("gen_ai.request.model", r"gen_ai\.request\.model"),
    ("gen_ai.usage.input_tokens", r"gen_ai\.usage\.input_tokens"),
    ("gen_ai.usage.output_tokens", r"gen_ai\.usage\.output_tokens"),
    ("gen_ai.response.finish_reasons", r"gen_ai\.response\.finish_reasons"),
]
FORENSIC = ["gen_ai.tool.call.arguments", "gen_ai.tool.call.result"]
DEPRECATED = ["gen_ai.system", "gen_ai.prompt", "gen_ai.completion"]

OK, NO, HM = "✓", "✗", "→"

# The forensic question is about ONE agent's tool spans. Everything reaches one collector,
# and otter-sre and goose both record tool content by design, so counting across the whole
# log says "content arrived on the MCP path" no matter what capybara-sre did. That was a
# standing false alarm telling the presenter to re-measure the talk's central finding.
SUBJECT = "capybara-sre"
_SERVICE = re.compile(r"-> service\.name: Str\(([^)]+)\)")


def only(text: str, service: str) -> str:
    """The parts of the collector's debug output belonging to one service.

    The debug exporter prints a `-> service.name: Str(x)` line per resource, so each block
    runs from one marker to the next. Crude, and it is reading a human-readable format that
    carries no stability promise -- but the alternative is asking the backend, and this
    script's whole point is checking what left the collector.
    """
    marks = list(_SERVICE.finditer(text))
    return "\n".join(
        text[m.start():(marks[i + 1].start() if i + 1 < len(marks) else len(text))]
        for i, m in enumerate(marks) if m.group(1) == service
    )


def read_source(arg: str | None) -> tuple[str, str]:
    if arg == "-":
        return sys.stdin.read(), "stdin"
    if arg:
        with open(arg) as f:
            return f.read(), arg
    # The collector runs in the cluster. This used to shell out to `docker logs capy-col`,
    # from when the stack was docker-compose; that container has not existed for a while and
    # the script simply failed with no arguments.
    #
    # --tail=-1 is the whole log, and it has to be. kubectl defaults to the most recent
    # lines, and with three agents plus the MCP servers sharing one collector the judge's
    # evaluation records scroll out of any fixed window within a couple of runs -- which
    # reads as "the judge emitted nothing" when it emitted exactly what it should.
    ns = os.environ.get("CAPYBARA_COLLECTOR_NS", "observability")
    selector = os.environ.get("CAPYBARA_COLLECTOR_SELECTOR",
                              "app.kubernetes.io/name=opentelemetry-collector")
    cmd = ["kubectl", "logs", "-n", ns, "-l", selector, "--tail=-1"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        sys.exit("kubectl not found — pass a file, or pipe collector output with '-'")
    if out.returncode != 0:
        sys.exit(f"could not read the collector's logs:\n  {' '.join(cmd)}\n"
                 f"{out.stderr.strip()}\n"
                 f"Is the cluster up? ./00_run.sh")
    return out.stdout + out.stderr, f"kubectl logs -n {ns} -l {selector}"


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("source", nargs="?", help="file with collector output, or '-' for stdin")
    ap.add_argument("--path", choices=["local", "mcp"],
                    default=os.environ.get("AGENT_TOOLS", "mcp").lower(),
                    help="which tool path the run used (default: $AGENT_TOOLS or mcp)")
    args = ap.parse_args()

    text, origin = read_source(args.source)
    if not text.strip():
        sys.exit(f"no output read from {origin} — did the run happen?")

    print(f"source     {origin}")
    print(f"tool path  {args.path}")
    print(f"{len(text.splitlines())} lines of collector output\n")

    print("CORE CONVENTIONS  (a conforming run must produce these)")
    missing = []
    for label, pattern in CORE:
        hit = re.search(pattern, text) is not None
        print(f"  {OK if hit else NO} {label}")
        if not hit:
            missing.append(label)

    print(f"\nFORENSIC CONTENT  (the local-vs-MCP experiment, {SUBJECT} only)")
    subject = only(text, SUBJECT)
    if not subject.strip():
        print(f"  {HM} no {SUBJECT} spans in this output — ask it something and re-run")
    counts = {a: len(re.findall(re.escape(a), subject)) for a in FORENSIC}
    for a, n in counts.items():
        print(f"  {OK if n else NO} {a:<28} {n} occurrence(s)")

    present = all(n > 0 for n in counts.values())
    if args.path == "local":
        matched = present
        verdict = ("as expected: locally declared @Tool methods go through ToolSpanWrapper, "
                   "which honours the two include-tool-* flags"
                   if matched else
                   "UNEXPECTED for the local path — the flags should have produced content here. "
                   "Check include-tool-arguments / include-tool-result are true.")
    else:
        matched = not present
        verdict = ("as expected: MCP tool calls route through TracingMcpClientListener, which "
                   "records the tool name and no content. Expected on this path, not a "
                   "broken setup"
                   if matched else
                   "UNEXPECTED for the MCP path — content arrived where we measured none. "
                   "quarkus-langchain4j may have fixed this; re-measure before presenting.")
    print(f"  {HM} {verdict}")

    print("\nEVALUATIONS")
    ev = len(re.findall(r"gen_ai\.evaluation\.result", text))
    names = sorted(set(re.findall(r"(root_cause_correctness|remediation_safety)", text)))
    print(f"  {OK if ev else NO} gen_ai.evaluation.result     {ev} reference(s)")
    if names:
        print(f"    dimensions seen: {', '.join(names)}")

    dep = [d for d in DEPRECATED if re.search(re.escape(d), text)]
    if dep:
        print("\nDEPRECATED KEYS STILL PRESENT")
        for d in dep:
            print(f"  {HM} {d} — replaced upstream; fine to observe, wrong to rely on")

    print()
    if missing:
        print(f"FAIL — {len(missing)} core convention(s) missing: {', '.join(missing)}")
        return 1
    if not matched:
        print("FAIL — forensic content did not match the expectation for this tool path (see above)")
        return 1
    print("PASS — core conventions present, forensic content matches the tool path under test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
