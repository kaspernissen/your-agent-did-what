package com.capybara.sre;

import com.capybara.db.CapybaraDatabase;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

/**
 * The same three capybara tools, registered as <em>locally declared</em>
 * LangChain4j {@code @Tool} methods instead of being reached over MCP.
 *
 * This class is the control arm of the talk's beat-4 experiment. The bodies
 * delegate to {@link CapybaraDatabase} from capybara-db-core — byte-for-byte the
 * same class the MCP server's tools call — so a run against these tools and a
 * run against the MCP tools differ in exactly one respect: how the tool was
 * registered, and therefore which piece of quarkus-langchain4j instrumentation
 * observes it.
 *
 *   local @Tool  → ToolSpanWrapper           → six attributes, arguments + result
 *   MCP tool     → TracingMcpClientListener  → tool name, and no content at all
 *
 * Same protocol-independent operation, same data, two span shapes. Switch with
 * {@code CAPYBARA_TOOLS=local|mcp} and diff the spans.
 */
@ApplicationScoped
public class CapybaraLocalTools {

    @Inject
    CapybaraDatabase db;

    @Tool("List all capybara customer records in the database.")
    public String list_records() {
        return db.listRecords().toString();
    }

    @Tool("Query capybara records, optionally filtered by plan (e.g. 'free' or 'pro').")
    public String query(@P(value = "plan to filter by, or omit for all", required = false) String plan) {
        return db.query(blankToNull(plan)).toString();
    }

    @Tool("Delete capybara records. With no plan, deletes ALL records. Destructive.")
    public String delete_records(@P(value = "plan whose records to delete; omit to delete ALL", required = false) String plan) {
        return db.deleteRecords(blankToNull(plan)).toString();
    }

    /** The model sometimes sends "" rather than omitting the argument; both mean "all". */
    private static String blankToNull(String s) {
        return (s == null || s.isBlank()) ? null : s;
    }
}
