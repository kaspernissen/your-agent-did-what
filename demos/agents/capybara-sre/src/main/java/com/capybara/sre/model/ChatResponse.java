package com.capybara.sre.model;

import java.util.List;

/**
 * What POST /chat returns.
 *
 * Note {@code toolCalls}: it carries each tool's name, arguments AND result. That
 * is the whole point of the comparison — the application knows exactly what it did,
 * and on the MCP path the span does not. The demo UI shows this list next to the
 * answer so the contrast is visible without a trace viewer.
 */
public record ChatResponse(String response,
                           List<ToolCall> toolCalls,
                           List<Evaluation> evaluations,
                           String toolPath,
                           String runId,
                           String traceId) {}
