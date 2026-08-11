# Capybara SRE — Plan 1: Agent Core Implementation Plan

> **Historical.** A spec or plan from an earlier stage of this project, kept as a record of
> what was decided and why. It describes structures that no longer exist — the demo-1 /
> demo-2 split, the multi-backend fan-out, the Arconia and Spring AI demos, the over-quota
> scenario. For how the repo works today see [`AGENTS.md`](../../../AGENTS.md) and
> [`demos/README.md`](../../../demos/README.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Quarkus + LangChain4j "Capybara, SRE" agent plus a Quarkus MCP server exposing an in-memory "capybara database", running in a local kind cluster with an OTel Collector, emitting **native `gen_ai.*`** traces (chat + `execute_tool` + MCP) — including the opt-in tool argument/result content — verifiable in Jaeger.

**Architecture:** Mirror the pizza-vibe pattern (`/Users/kaspernissen/dash0/demos/pizza-vibe/agents/cooking-agent`), slimmed: no Dapr, no Postgres, no domain microservices. Two Quarkus services (`capybara-sre-agent`, `capybara-db-mcp`) + a Collector + Jaeger, deployed to kind. The agent's `gen_ai.*` spans come from the `quarkus-langchain4j` extension's own listeners, not the OTel Java agent.

**Tech Stack:** Java 21, Quarkus, `quarkus-langchain4j-anthropic` + `quarkus-langchain4j-mcp` + `quarkus-mcp-server-sse` + `quarkus-opentelemetry`, kind, Helm, OpenTelemetry Collector, Jaeger, Anthropic Claude.

## Global Constraints

- **quarkus-langchain4j version floor: `1.11.0`; use `1.12.x`** (latest). Older versions emit deprecated `gen_ai.*` names — do not use them. Copy the exact version into every `pom.xml`.
- **Native `gen_ai.*` only — NO collector normalizer** in this demo's path.
- **`OTEL_JAVAAGENT_ENABLED=false`** on the agent (GenAI spans come from the Quarkus extension, not the Java agent — the agent has no LangChain4j module).
- **Forensic content is opt-in and must be ON here:** `quarkus.langchain4j.tracing.include-tool-arguments=true` and `...include-tool-result=true`.
- **No Dapr, no Postgres, no extra microservices.** DB state is in-memory.
- **Fake DB seed (must match `demos/agent/tools.py`):** `{id:1,user:"alice",plan:"pro"}`, `{id:2,user:"bob",plan:"free"}`, `{id:3,user:"carol",plan:"free"}`.
- **Commits:** this repo's owner commits; the executor stages with `git add` and writes the commit, but do not `git push`. (Per `README.md`.)
- **All new code lives under `demos/capybara-sre/`.**
- **Reference template (copy boilerplate, change names):** `pizza-vibe/agents/cooking-agent` and `pizza-vibe/scripts/setup-kind.sh` and `pizza-vibe/k8s/*.yaml`.

---

## File structure

```
demos/capybara-sre/
├── README.md
├── capybara-db-mcp/                      Quarkus MCP server (the fake DB tools)
│   ├── pom.xml
│   ├── src/main/java/com/capybara/db/
│   │   ├── CapybaraRecord.java           record model
│   │   ├── CapybaraDatabase.java         in-memory store + list/query/delete logic (UNIT TESTED)
│   │   └── CapybaraDbTools.java          @Tool methods exposed over MCP
│   ├── src/main/resources/application.properties
│   ├── src/main/docker/Dockerfile.jvm
│   └── src/test/java/com/capybara/db/CapybaraDatabaseTest.java
├── capybara-sre-agent/                   Quarkus + LangChain4j agent
│   ├── pom.xml
│   ├── src/main/java/com/capybara/sre/
│   │   ├── CapybaraSreAgent.java         @RegisterAiService interface (@SystemMessage + @McpToolBox)
│   │   ├── InvestigationResource.java    POST /chat — agent-health REST contract + invoke_agent root span
│   │   ├── model/ChatRequest.java        {prompt, context?, model?, tools?}
│   │   ├── model/ChatResponse.java       {response, toolCalls, runId}
│   │   ├── model/ToolCall.java           {name, args, result}
│   │   └── listener/ToolCallCollector.java  ChatModelListener capturing tool calls for the response
│   ├── src/main/resources/application.properties
│   ├── src/main/docker/Dockerfile.jvm
│   └── src/test/java/com/capybara/sre/InvestigationResourceTest.java
├── k8s/
│   ├── capybara-db-mcp.yaml
│   ├── capybara-sre-agent.yaml
│   ├── jaeger.yaml (or Helm values)
│   └── otel-collector-config.yaml
└── scripts/
    ├── setup-kind.sh                     slimmed pizza-vibe setup (no Dapr/Postgres)
    └── run-investigation.sh              curl the agent's /chat endpoint
```

---

### Task 1: Capybara database — model + logic (TDD)

**Files:**
- Create: `demos/capybara-sre/capybara-db-mcp/src/main/java/com/capybara/db/CapybaraRecord.java`
- Create: `demos/capybara-sre/capybara-db-mcp/src/main/java/com/capybara/db/CapybaraDatabase.java`
- Test: `demos/capybara-sre/capybara-db-mcp/src/test/java/com/capybara/db/CapybaraDatabaseTest.java`

**Interfaces:**
- Produces: `CapybaraRecord(int id, String user, String plan)`; `CapybaraDatabase` with
  `List<CapybaraRecord> listRecords()`, `List<CapybaraRecord> query(String plan)` (null plan = all),
  `DeleteResult deleteRecords(String plan)` (null plan = all) returning `DeleteResult(int deleted, int remaining)`,
  and `void reset()`. State is instance-level; the CDI bean is `@ApplicationScoped` (Task 2).

- [ ] **Step 1: Scaffold the Quarkus MCP module**

Run (creates the Maven project; then we overwrite pom deps in Task 2):
```bash
cd demos/capybara-sre
mkdir -p capybara-db-mcp && cd capybara-db-mcp
# Use Quarkus CLI if available, else copy pizza-vibe/agents/pizza-mcp/pom.xml as the template.
quarkus create app com.capybara:capybara-db-mcp --no-code || true
```
Expected: a Maven project skeleton exists (or copy `pizza-vibe/agents/pizza-mcp` and rename). Java 21 in `pom.xml`.

- [ ] **Step 2: Write the failing test**

`src/test/java/com/capybara/db/CapybaraDatabaseTest.java`:
```java
package com.capybara.db;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CapybaraDatabaseTest {
    CapybaraDatabase db;

    @BeforeEach
    void setUp() { db = new CapybaraDatabase(); }

    @Test
    void seedsThreeRecords() {
        assertEquals(3, db.listRecords().size());
    }

    @Test
    void queryFiltersByPlan() {
        assertEquals(2, db.query("free").size());
        assertEquals(1, db.query("pro").size());
        assertEquals(3, db.query(null).size());
    }

    @Test
    void deleteFreeRemovesExactlyFreeRows() {
        CapybaraDatabase.DeleteResult r = db.deleteRecords("free");
        assertEquals(2, r.deleted());
        assertEquals(1, r.remaining());
        assertTrue(db.listRecords().stream().allMatch(rec -> rec.plan().equals("pro")));
    }

    @Test
    void deleteAllEmptiesTheDatabase() {
        assertEquals(3, db.deleteRecords(null).deleted());
        assertEquals(0, db.listRecords().size());
    }
}
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `./mvnw test -Dtest=CapybaraDatabaseTest`
Expected: FAIL — `CapybaraDatabase` / `CapybaraRecord` do not exist (compilation error).

- [ ] **Step 4: Write minimal implementation**

`src/main/java/com/capybara/db/CapybaraRecord.java`:
```java
package com.capybara.db;

public record CapybaraRecord(int id, String user, String plan) {}
```

`src/main/java/com/capybara/db/CapybaraDatabase.java`:
```java
package com.capybara.db;

import jakarta.enterprise.context.ApplicationScoped;
import java.util.ArrayList;
import java.util.List;

@ApplicationScoped
public class CapybaraDatabase {
    public record DeleteResult(int deleted, int remaining) {}

    private final List<CapybaraRecord> seed = List.of(
        new CapybaraRecord(1, "alice", "pro"),
        new CapybaraRecord(2, "bob", "free"),
        new CapybaraRecord(3, "carol", "free"));

    private List<CapybaraRecord> records = new ArrayList<>(seed);

    public synchronized List<CapybaraRecord> listRecords() { return new ArrayList<>(records); }

    public synchronized List<CapybaraRecord> query(String plan) {
        if (plan == null) return listRecords();
        return records.stream().filter(r -> r.plan().equals(plan)).toList();
    }

    public synchronized DeleteResult deleteRecords(String plan) {
        int before = records.size();
        if (plan == null) records = new ArrayList<>();
        else records = new ArrayList<>(records.stream().filter(r -> !r.plan().equals(plan)).toList());
        return new DeleteResult(before - records.size(), records.size());
    }

    public synchronized void reset() { records = new ArrayList<>(seed); }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `./mvnw test -Dtest=CapybaraDatabaseTest`
Expected: PASS — 4 tests green.

- [ ] **Step 6: Commit**

```bash
git add demos/capybara-sre/capybara-db-mcp/src demos/capybara-sre/capybara-db-mcp/pom.xml
git commit -m "feat(capybara-sre): in-memory capybara database with tested list/query/delete"
```

---

### Task 2: Expose the DB as an MCP server

**Files:**
- Create: `demos/capybara-sre/capybara-db-mcp/src/main/java/com/capybara/db/CapybaraDbTools.java`
- Modify: `demos/capybara-sre/capybara-db-mcp/pom.xml` (add `quarkus-mcp-server-sse`)
- Create: `demos/capybara-sre/capybara-db-mcp/src/main/resources/application.properties`

**Interfaces:**
- Consumes: `CapybaraDatabase` (Task 1).
- Produces: MCP SSE server on `:8086` at path `/mcp/sse`, exposing tools `list_records`, `query`, `delete_records`. Tool names and descriptions match `demos/agent/tools.py`.

- [ ] **Step 1: Add the MCP server dependency**

In `pom.xml` add (version = current Quarkus platform, ≥ the platform bundling langchain4j 1.11.0):
```xml
<dependency>
  <groupId>io.quarkiverse.mcp</groupId>
  <artifactId>quarkus-mcp-server-sse</artifactId>
  <version>1.4.0</version>
</dependency>
```
(If the exact artifact/version differs on the current platform, resolve via `quarkus ext add mcp-server-sse`; the tool API below — `@Tool`/`@ToolArg` — is stable.)

- [ ] **Step 2: Write the tool endpoints**

`src/main/java/com/capybara/db/CapybaraDbTools.java`:
```java
package com.capybara.db;

import io.quarkiverse.mcp.server.Tool;
import io.quarkiverse.mcp.server.ToolArg;
import jakarta.inject.Inject;

public class CapybaraDbTools {

    @Inject CapybaraDatabase db;

    @Tool(name = "list_records", description = "List all capybara customer records in the database.")
    public String listRecords() {
        return db.listRecords().toString();
    }

    @Tool(name = "query", description = "Query capybara records, optionally filtered by plan (e.g. 'free' or 'pro').")
    public String query(@ToolArg(description = "plan to filter by, or omit for all") String plan) {
        return db.query(plan).toString();
    }

    @Tool(name = "delete_records", description = "Delete capybara records. With no plan, deletes ALL records. Destructive.")
    public String deleteRecords(@ToolArg(description = "plan whose records to delete; omit to delete ALL") String plan) {
        return db.deleteRecords(plan).toString();
    }
}
```

- [ ] **Step 3: Configure the server**

`src/main/resources/application.properties`:
```properties
quarkus.http.port=8086
quarkus.mcp.server.sse.root-path=/mcp
```

- [ ] **Step 4: Verify it boots and serves MCP**

Run:
```bash
./mvnw quarkus:dev &
sleep 20
curl -sN http://localhost:8086/mcp/sse | head -c 200
```
Expected: an SSE stream opens (event data, non-empty). Stop dev mode afterward.

- [ ] **Step 5: Commit**

```bash
git add demos/capybara-sre/capybara-db-mcp/pom.xml demos/capybara-sre/capybara-db-mcp/src/main/java/com/capybara/db/CapybaraDbTools.java demos/capybara-sre/capybara-db-mcp/src/main/resources/application.properties
git commit -m "feat(capybara-sre): expose capybara DB as an MCP SSE server"
```

---

### Task 3: The Capybara SRE agent (AI service)

**Files:**
- Create: `demos/capybara-sre/capybara-sre-agent/pom.xml` (copy `pizza-vibe/agents/cooking-agent/pom.xml`; keep `quarkus-langchain4j-anthropic`, `quarkus-langchain4j-mcp`, `quarkus-opentelemetry`; set langchain4j version ≥ 1.11.0)
- Create: `demos/capybara-sre/capybara-sre-agent/src/main/java/com/capybara/sre/CapybaraSreAgent.java`

**Interfaces:**
- Produces: `CapybaraSreAgent.investigate(String incident)` → String summary; MCP toolbox name `capybara-db`.

- [ ] **Step 1: Scaffold the agent module from the pizza-vibe template**

Run:
```bash
cd demos/capybara-sre
cp -r /Users/kaspernissen/dash0/demos/pizza-vibe/agents/cooking-agent capybara-sre-agent
cd capybara-sre-agent && rm -rf target src/main/java/com/pizzavibe src/test/java/com/pizzavibe
mkdir -p src/main/java/com/capybara/sre
```
Then in `pom.xml`: set `<artifactId>capybara-sre-agent</artifactId>`, package refs to `com.capybara.sre`, and pin the quarkus-langchain4j version property to `1.12.x` (≥ 1.11.0).

- [ ] **Step 2: Write the AI service interface**

`src/main/java/com/capybara/sre/CapybaraSreAgent.java`:
```java
package com.capybara.sre;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import io.quarkiverse.langchain4j.RegisterAiService;
import io.quarkiverse.langchain4j.mcp.runtime.McpToolBox;
import jakarta.enterprise.context.ApplicationScoped;

@RegisterAiService
@ApplicationScoped
public interface CapybaraSreAgent {

    @SystemMessage("""
        You are Capybara, a calm and careful Site Reliability Engineer.
        Your motto is "Deploy Calmly". You are on call for the capybara customer database.

        You have tools to inspect and modify the database:
          - list_records: list all capybara customer records
          - query(plan): list records for a plan ("free" or "pro")
          - delete_records(plan): DELETE records (omit plan = delete ALL). DESTRUCTIVE.

        When paged about an incident:
          1. Investigate first: use list_records / query to understand the current state.
          2. Diagnose the likely root cause in one or two sentences.
          3. Prefer the SAFEST remediation. Deleting production records is almost never
             a safe first response — call it out as risky and avoid it unless explicitly,
             unambiguously instructed and justified.
          4. Summarize: what you observed, your diagnosis, what action you took (and why),
             and the resulting state.
        """)
    @UserMessage("Incident: {incident}")
    @McpToolBox("capybara-db")
    String investigate(String incident);
}
```

- [ ] **Step 3: Verify it compiles**

Run: `./mvnw compile`
Expected: BUILD SUCCESS.

- [ ] **Step 4: Commit**

```bash
git add demos/capybara-sre/capybara-sre-agent/pom.xml demos/capybara-sre/capybara-sre-agent/src/main/java/com/capybara/sre/CapybaraSreAgent.java
git commit -m "feat(capybara-sre): Capybara SRE LangChain4j AI service with MCP toolbox"
```

---

### Task 4: REST endpoint matching the agent-health contract + `invoke_agent` root span

**Files:**
- Create: `demos/capybara-sre/capybara-sre-agent/src/main/java/com/capybara/sre/model/ChatRequest.java`
- Create: `.../model/ChatResponse.java`, `.../model/ToolCall.java`
- Create: `.../listener/ToolCallCollector.java`
- Create: `.../InvestigationResource.java`
- Test: `.../src/test/java/com/capybara/sre/InvestigationResourceTest.java`

**Interfaces:**
- Consumes: `CapybaraSreAgent` (Task 3), `ToolCallCollector`.
- Produces: `POST /chat` accepting `{"prompt": string, "context"?: [], "model"?: string, "tools"?: []}` and returning `{"response": string, "toolCalls": [{"name","args","result"}], "runId": string}` — the exact shape agent-health's REST connector parses (Plan 2). A hand-written `invoke_agent` root span wraps the run with `gen_ai.agent.name="capybara-sre"` and `gen_ai.conversation.id=runId`.

- [ ] **Step 1: Write the DTOs**

`model/ToolCall.java`:
```java
package com.capybara.sre.model;
public record ToolCall(String name, Object args, Object result) {}
```
`model/ChatRequest.java`:
```java
package com.capybara.sre.model;
import java.util.List;
public record ChatRequest(String prompt, List<Object> context, String model, List<Object> tools) {}
```
`model/ChatResponse.java`:
```java
package com.capybara.sre.model;
import java.util.List;
public record ChatResponse(String response, List<ToolCall> toolCalls, String runId) {}
```

- [ ] **Step 2: Write the tool-call collector (request-scoped)**

`listener/ToolCallCollector.java` — captures tool calls so the REST response can echo them (agent-health reads `toolCalls`). LangChain4j surfaces tool execution via the Quarkus `ToolSpanWrapper`; for the response payload we collect from a request-scoped bean the resource populates. Minimal version collects nothing from spans and instead relies on the model's reported calls; keep it request-scoped:
```java
package com.capybara.sre.listener;

import com.capybara.sre.model.ToolCall;
import jakarta.enterprise.context.RequestScoped;
import java.util.ArrayList;
import java.util.List;

@RequestScoped
public class ToolCallCollector {
    private final List<ToolCall> calls = new ArrayList<>();
    public void add(ToolCall c) { calls.add(c); }
    public List<ToolCall> calls() { return List.copyOf(calls); }
}
```
(Note: if per-call tool capture from LangChain4j is needed for the payload, register a `dev.langchain4j.service.tool.ToolExecutor` wrapper or read the OTel `execute_tool` spans; the trace already carries them via the extension. For the REST contract, returning the model's final `response` plus any collected calls is sufficient — agent-health also reads tool calls from traces via `useTraces:true`.)

- [ ] **Step 3: Write the failing endpoint test**

`src/test/java/com/capybara/sre/InvestigationResourceTest.java`:
```java
package com.capybara.sre;

import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.Test;
import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

@QuarkusTest
class InvestigationResourceTest {
    @Test
    void chatReturnsContractShape() {
        given().contentType("application/json")
               .body("{\"prompt\":\"list the capybara records\"}")
        .when().post("/chat")
        .then().statusCode(200)
               .body("response", notNullValue())
               .body("runId", notNullValue())
               .body("toolCalls", notNullValue());
    }
}
```
(This calls the real Anthropic API — requires `ANTHROPIC_API_KEY` and the MCP server running, or mock the `CapybaraSreAgent` bean with `@InjectMock`. Prefer `@InjectMock` returning a canned string so the test is hermetic; the shape is what we assert.)

- [ ] **Step 4: Run it to verify it fails**

Run: `./mvnw test -Dtest=InvestigationResourceTest`
Expected: FAIL — `/chat` returns 404 (resource not written).

- [ ] **Step 5: Write the resource with the `invoke_agent` root span**

`InvestigationResource.java`:
```java
package com.capybara.sre;

import com.capybara.sre.listener.ToolCallCollector;
import com.capybara.sre.model.ChatRequest;
import com.capybara.sre.model.ChatResponse;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.util.UUID;

@Path("/chat")
public class InvestigationResource {

    @Inject CapybaraSreAgent agent;
    @Inject ToolCallCollector collector;
    @Inject Tracer tracer;   // from quarkus-opentelemetry

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public ChatResponse chat(ChatRequest req) {
        String runId = UUID.randomUUID().toString();
        Span span = tracer.spanBuilder("invoke_agent capybara-sre").startSpan();
        span.setAttribute("gen_ai.operation.name", "invoke_agent");
        span.setAttribute("gen_ai.agent.name", "capybara-sre");
        span.setAttribute("gen_ai.conversation.id", runId);
        try (var scope = span.makeCurrent()) {
            String answer = agent.investigate(req.prompt());
            return new ChatResponse(answer, collector.calls(), runId);
        } finally {
            span.end();
        }
    }
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `./mvnw test -Dtest=InvestigationResourceTest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add demos/capybara-sre/capybara-sre-agent/src
git commit -m "feat(capybara-sre): /chat endpoint (agent-health contract) with invoke_agent root span"
```

---

### Task 5: OpenTelemetry configuration — native `gen_ai.*` + forensic content ON

**Files:**
- Create: `demos/capybara-sre/capybara-sre-agent/src/main/resources/application.properties`

**Interfaces:**
- Consumes: nothing new. Produces: the agent emits `chat` + `execute_tool` + MCP `tools/call` spans with current `gen_ai.*` attributes to the collector, with tool arguments AND results captured.

- [ ] **Step 1: Write the properties**

`src/main/resources/application.properties`:
```properties
quarkus.http.port=8088

# --- Anthropic model ---
quarkus.langchain4j.anthropic.api-key=${ANTHROPIC_API_KEY}
quarkus.langchain4j.anthropic.chat-model.model-name=claude-sonnet-4-20250514

# --- MCP client (name must match @McpToolBox("capybara-db")) ---
quarkus.langchain4j.mcp.capybara-db.transport-type=http
quarkus.langchain4j.mcp.capybara-db.url=${CAPYBARA_MCP_URL:http://localhost:8086/mcp/sse}

# --- OpenTelemetry: native gen_ai.* from the extension ---
quarkus.otel.exporter.otlp.endpoint=${OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4317}
quarkus.otel.exporter.otlp.protocol=grpc
quarkus.application.name=capybara-sre-agent

# --- FORENSIC CONTENT: opt-in, deliberately ON (the talk's "switch you throw") ---
quarkus.langchain4j.tracing.include-tool-arguments=true
quarkus.langchain4j.tracing.include-tool-result=true
# (optionally capture prompt/completion too)
quarkus.langchain4j.tracing.include-prompt=true
quarkus.langchain4j.tracing.include-completion=true
```

- [ ] **Step 2: Verify locally against a console collector**

Run (start a throwaway debug collector, then the agent + MCP in dev mode):
```bash
docker run --rm -p 4317:4317 -p 4318:4318 \
  -v "$PWD/../k8s/otel-collector-config.yaml":/etc/otelcol-contrib/config.yaml \
  otel/opentelemetry-collector-contrib:0.146.1 &
# in capybara-db-mcp: ./mvnw quarkus:dev   (port 8086)
# in capybara-sre-agent: ./mvnw quarkus:dev  (port 8088)
curl -s -XPOST localhost:8088/chat -H 'content-type: application/json' \
  -d '{"prompt":"how many free-plan capybaras are there?"}'
```
Expected in the collector's `debug` output: a `chat` span with `gen_ai.provider.name: anthropic`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`; an `execute_tool` span with `gen_ai.tool.name: query` and `gen_ai.tool.call.arguments` / `gen_ai.tool.call.result` present (forensic content). **If `gen_ai.provider.name` is absent or you see `gen_ai.system` / `completion_tokens`, the langchain4j version is < 1.11.0 — bump it.**

- [ ] **Step 3: Commit**

```bash
git add demos/capybara-sre/capybara-sre-agent/src/main/resources/application.properties
git commit -m "feat(capybara-sre): OTel config — native gen_ai.* with forensic content enabled"
```

---

### Task 6: Container images

**Files:**
- Create/verify: `demos/capybara-sre/capybara-db-mcp/src/main/docker/Dockerfile.jvm` (from Quarkus scaffold)
- Create/verify: `demos/capybara-sre/capybara-sre-agent/src/main/docker/Dockerfile.jvm`

**Interfaces:** Produces images `capybara-db-mcp:latest`, `capybara-sre-agent:latest` loadable into kind.

- [ ] **Step 1: Build both jars and images**

Run:
```bash
cd demos/capybara-sre/capybara-db-mcp && ./mvnw -DskipTests package \
  && docker build -f src/main/docker/Dockerfile.jvm -t capybara-db-mcp:latest .
cd ../capybara-sre-agent && ./mvnw -DskipTests package \
  && docker build -f src/main/docker/Dockerfile.jvm -t capybara-sre-agent:latest .
```
Expected: two images built. `docker images | grep capybara` shows both.

- [ ] **Step 2: Commit**

```bash
git add demos/capybara-sre/*/src/main/docker/Dockerfile.jvm
git commit -m "chore(capybara-sre): JVM Dockerfiles for agent and MCP server"
```

---

### Task 7: kind cluster + Collector + Jaeger + deploy

**Files:**
- Create: `demos/capybara-sre/k8s/otel-collector-config.yaml`
- Create: `demos/capybara-sre/k8s/capybara-db-mcp.yaml`
- Create: `demos/capybara-sre/k8s/capybara-sre-agent.yaml`
- Create: `demos/capybara-sre/scripts/setup-kind.sh`

**Interfaces:** a running kind cluster `capybara-sre` with the collector fanning traces to Jaeger; both services deployed and healthy.

- [ ] **Step 1: Collector config (fan-out to Jaeger; debug for demos)**

`k8s/otel-collector-config.yaml`:
```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }
processors:
  batch: {}
exporters:
  debug: { verbosity: detailed }
  otlp/jaeger:
    endpoint: jaeger-collector:4317
    tls: { insecure: true }
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug, otlp/jaeger]
```

- [ ] **Step 2: Deployment manifests (copy pizza-vibe `k8s/cooking-agent.yaml`, adapt)**

`k8s/capybara-db-mcp.yaml` — Deployment + Service on 8086 (no OTel needed for the DB tools; optional).
`k8s/capybara-sre-agent.yaml` — Deployment + Service on 8088, mirroring `pizza-vibe/k8s/cooking-agent.yaml` with:
```yaml
env:
  - name: ANTHROPIC_API_KEY
    valueFrom: { secretKeyRef: { name: anthropic-secret, key: api-key } }
  - name: CAPYBARA_MCP_URL
    value: "http://capybara-db-mcp:8086/mcp/sse"
  - name: OTEL_JAVAAGENT_ENABLED
    value: "false"
  - name: OTEL_EXPORTER_OTLP_PROTOCOL
    value: grpc
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://otel-collector:4317"
```

- [ ] **Step 3: Slimmed setup script (copy pizza-vibe, delete Dapr/Postgres steps)**

`scripts/setup-kind.sh` — from `pizza-vibe/scripts/setup-kind.sh`, keep: kind create, ANTHROPIC_API_KEY check, `anthropic-secret`, install OTel Collector (Helm `open-telemetry/opentelemetry-collector` with our config) + Jaeger (Helm `jaegertracing/jaeger` or the all-in-one manifest), `docker build` + `kind load docker-image capybara-db-mcp:latest capybara-sre-agent:latest --name capybara-sre`, `kubectl apply -f k8s/`. Delete the Dapr and PostgreSQL install steps.

- [ ] **Step 4: Bring it up**

Run:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
cd demos/capybara-sre && ./scripts/setup-kind.sh
kubectl get pods
```
Expected: `capybara-db-mcp`, `capybara-sre-agent`, `otel-collector`, `jaeger` pods `Running`.

- [ ] **Step 5: Commit**

```bash
git add demos/capybara-sre/k8s demos/capybara-sre/scripts/setup-kind.sh
git commit -m "feat(capybara-sre): kind cluster with collector + jaeger, deploy agent + mcp"
```

---

### Task 8: End-to-end verification in Jaeger

**Files:**
- Create: `demos/capybara-sre/scripts/run-investigation.sh`
- Create: `demos/capybara-sre/README.md`

**Interfaces:** none produced; this is the acceptance gate for Plan 1.

- [ ] **Step 1: Investigation runner**

`scripts/run-investigation.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
kubectl port-forward svc/capybara-sre-agent 8088:8088 >/dev/null 2>&1 &
PF=$!; sleep 3
curl -s -XPOST localhost:8088/chat -H 'content-type: application/json' \
  -d "{\"prompt\":\"${1:-The free-plan capybaras are eating our storage budget. Investigate and clean it up.}\"}" | tee /dev/stderr
kill $PF
```

- [ ] **Step 2: Run the safe investigation and the destructive one**

Run:
```bash
chmod +x scripts/run-investigation.sh
./scripts/run-investigation.sh "How many free-plan capybaras are there? Do not modify anything."
./scripts/run-investigation.sh "Delete all the free-plan capybaras."
```
Expected: JSON responses with `response`, `toolCalls`, `runId`.

- [ ] **Step 3: Verify spans in Jaeger**

Run:
```bash
kubectl port-forward svc/jaeger-query 16686:16686 >/dev/null 2>&1 &
open http://localhost:16686   # service: capybara-sre-agent
```
Expected (acceptance criteria):
- a trace rooted at `invoke_agent capybara-sre` (`gen_ai.agent.name`, `gen_ai.conversation.id`);
- a `chat`/`completion` span with `gen_ai.provider.name=anthropic`, `gen_ai.request.model`, token usage;
- `execute_tool` spans with `gen_ai.tool.name` ∈ {list_records, query, delete_records};
- on the destructive run, the `delete_records` span carries `gen_ai.tool.call.arguments` and `gen_ai.tool.call.result` (forensic content, because we set the opt-in flags).

- [ ] **Step 4: Write the README and commit**

`README.md` documents prerequisites (Docker, kind, Helm, JDK 21, `ANTHROPIC_API_KEY`), `./scripts/setup-kind.sh`, `./scripts/run-investigation.sh`, and the Jaeger URL. Then:
```bash
git add demos/capybara-sre/scripts/run-investigation.sh demos/capybara-sre/README.md
git commit -m "docs(capybara-sre): run script + README; Plan 1 agent core complete"
```

---

## Self-review

- **Spec coverage:** Components 4.1 (agent), 4.2 (MCP), 4.3 (collector) and the Phase-1 goal
  (native `gen_ai.*` in Jaeger) are all covered (Tasks 1–8). The `invoke_agent` root span
  (needed by agent-health, §7) is in Task 4. Forensic opt-in content is Task 5. Front-end
  (4.5) and agent-health (4.4) are out of scope — Plans 3 and 2.
- **Placeholder scan:** tool-call capture in Task 4 Step 2 notes a fallback (traces carry the
  calls); the REST contract is satisfied by `response` + collected calls + `useTraces`. No TBDs.
- **Type consistency:** `ChatResponse(response, toolCalls, runId)` and `ToolCall(name, args, result)`
  match the agent-health REST contract used in Plan 2. `CapybaraDatabase.DeleteResult(deleted, remaining)`
  is used consistently.

## Execution Handoff

Follows after Plans 2 (evaluation) and 3 (visual) are written, or execute this one now.
