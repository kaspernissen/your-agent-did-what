package com.capybara.sre;

import dev.langchain4j.service.Result;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import io.quarkiverse.langchain4j.RegisterAiService;
import io.quarkiverse.langchain4j.mcp.runtime.McpToolBox;
import jakarta.enterprise.context.ApplicationScoped;

/**
 * Capybara SRE reaching its tools over MCP.
 *
 * Tool calls here route through TracingMcpClientListener, which records the tool
 * name and no content — even with include-tool-arguments and include-tool-result
 * both true. Compare with {@link CapybaraSreAgentLocal}, which is identical apart
 * from the toolbox.
 */
@RegisterAiService
@ApplicationScoped
public interface CapybaraSreAgent {

    @SystemMessage(CapybaraPrompt.SYSTEM)
    @UserMessage("Incident: {incident}")
    @McpToolBox("capybara-db")
    Result<String> investigate(String incident);
}
