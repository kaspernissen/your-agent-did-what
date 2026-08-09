"""Same fake-database agent as Demo 1, but instrumented with OpenInference
(emits llm.* / openinference.* attributes) so the normalizer has something to rewrite."""
import json, os, sys
import anthropic
from openinference.instrumentation.anthropic import AnthropicInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))
import tools  # reuse Demo 1's tool module

endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
trace.set_tracer_provider(provider)
AnthropicInstrumentor().instrument(tracer_provider=provider)

client = anthropic.Anthropic()

def run(prompt):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(6):
        resp = client.messages.create(model=os.environ.get("DEMO_MODEL", "claude-sonnet-5"),
                                      max_tokens=1024, tools=tools.TOOL_SCHEMAS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        tus = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if not tus:
            return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(tools.dispatch(b.name)(**(b.input or {})))}
            for b in tus]})

if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "List all records."))
