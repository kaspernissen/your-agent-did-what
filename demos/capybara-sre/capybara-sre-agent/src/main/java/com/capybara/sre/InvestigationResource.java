package com.capybara.sre;

import com.capybara.sre.model.ChatRequest;
import com.capybara.sre.model.ChatResponse;
import com.capybara.sre.model.ToolCall;
import dev.langchain4j.service.Result;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Path("/chat")
public class InvestigationResource {

    @Inject
    CapybaraSreAgent agent;

    @Inject
    Tracer tracer;

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
            Result<String> r = agent.investigate(req.prompt());
            String text = r.content();
            List<ToolCall> toolCalls = r.toolExecutions() == null
                    ? List.of()
                    : r.toolExecutions().stream()
                            .map(te -> new ToolCall(
                                    te.request().name(),
                                    te.request().arguments(),
                                    te.result()))
                            .collect(Collectors.toList());
            return new ChatResponse(text, toolCalls, runId);
        } finally {
            span.end();
        }
    }
}
