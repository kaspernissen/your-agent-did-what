package com.capybara.sre.model;

import java.util.List;

public record ChatResponse(String response, List<ToolCall> toolCalls, String runId) {}
