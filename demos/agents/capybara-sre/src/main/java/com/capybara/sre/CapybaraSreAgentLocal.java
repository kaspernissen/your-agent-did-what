package com.capybara.sre;

import dev.langchain4j.service.Result;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import io.quarkiverse.langchain4j.RegisterAiService;
import jakarta.enterprise.context.ApplicationScoped;

/**
 * Capybara SRE reaching the same tools as locally declared @Tool methods.
 *
 * Identical to {@link CapybaraSreAgent} — same model, same prompt, same three
 * operations over the same {@code CapybaraDatabase} — except that the tools are
 * registered here rather than fetched over MCP. Tool calls therefore go through
 * ToolSpanWrapper, which DOES honour include-tool-arguments and
 * include-tool-result.
 *
 * The pair is the experiment: one variable, two span shapes.
 */
@RegisterAiService(tools = CapybaraLocalTools.class)
@ApplicationScoped
public interface CapybaraSreAgentLocal {

    @SystemMessage(CapybaraPrompt.SYSTEM)
    @UserMessage("Incident: {incident}")
    Result<String> investigate(String incident);
}
