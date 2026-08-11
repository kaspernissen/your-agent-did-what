package com.capybara.sre;

import com.capybara.sre.model.ChatRequest;
import com.capybara.sre.model.ChatResponse;
import com.capybara.sre.model.Evaluation;
import com.capybara.sre.model.ToolCall;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.service.Result;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Path("/chat")
public class InvestigationResource {

    @Inject
    CapybaraSreAgent mcpAgent;

    @Inject
    CapybaraSreAgentLocal localAgent;

    /**
     * Which tool path this run uses: "mcp" (default) or "local".
     *
     * The two agents are identical apart from tool registration, so flipping this
     * and re-running the same incident produces two traces whose only meaningful
     * difference is whether the execute_tool spans carry
     * gen_ai.tool.call.arguments and gen_ai.tool.call.result.
     */
    @ConfigProperty(name = "capybara.tools", defaultValue = "mcp")
    String toolPath;

    @Inject
    Tracer tracer;

    @Inject
    ObjectMapper objectMapper;

    @Inject
    CapybaraJudge judge;

    @Inject
    EvaluationEmitter evaluations;

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public ChatResponse chat(ChatRequest req) {
        String runId = UUID.randomUUID().toString();
        boolean local = "local".equalsIgnoreCase(toolPath);
        Span span = tracer.spanBuilder("invoke_agent capybara-sre").startSpan();
        span.setAttribute("gen_ai.operation.name", "invoke_agent");
        span.setAttribute("gen_ai.agent.name", "capybara-sre");
        span.setAttribute("gen_ai.conversation.id", runId);
        // Not a GenAI convention attribute — it is how we tell the two runs apart
        // when diffing their traces side by side.
        span.setAttribute("capybara.tool_path", local ? "local" : "mcp");
        try (var scope = span.makeCurrent()) {
            Result<String> r = local ? localAgent.investigate(req.prompt())
                                     : mcpAgent.investigate(req.prompt());
            String text = r.content();
            List<ToolCall> toolCalls = r.toolExecutions() == null
                    ? List.of()
                    : r.toolExecutions().stream()
                            .map(te -> {
                                String argsJson = te.request().arguments();
                                Object args;
                                if (argsJson == null || argsJson.isBlank()) {
                                    args = Map.of();
                                } else {
                                    try {
                                        args = objectMapper.readValue(argsJson, Object.class);
                                    } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
                                        args = argsJson;
                                    }
                                }
                                return new ToolCall(te.request().name(), args, te.result());
                            })
                            .toList();
            // Judge the completed run and attach gen_ai.evaluation.result events to
            // this span BEFORE it ends, which is what the spec's parenting guidance
            // asks for. A judge failure must never fail the investigation.
            List<Evaluation> verdicts = List.of();
            try {
                String verdict = judge.judge(req.prompt(),
                        objectMapper.writeValueAsString(toolCalls), text);
                verdicts = evaluations.emit(span, verdict);
            } catch (Exception e) {
                evaluations.emitFailure(span, e);
            }

            return new ChatResponse(text, toolCalls, verdicts, local ? "local" : "mcp", runId,
                    span.getSpanContext().getTraceId());
        } finally {
            span.end();
        }
    }
}
