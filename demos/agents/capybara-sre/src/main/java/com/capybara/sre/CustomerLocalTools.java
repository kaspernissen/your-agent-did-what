package com.capybara.sre;

import com.customerdb.CustomerDatabase;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

/**
 * The same four tools, registered as <em>locally declared</em>
 * LangChain4j {@code @Tool} methods instead of being reached over MCP.
 *
 * This is the control arm of a controlled comparison. The bodies
 * delegate to {@link CustomerDatabase} from customer-db-core — byte-for-byte the
 * same class the MCP server's tools call — so a run against these tools and a
 * run against the MCP tools differ in exactly one respect: how the tool was
 * registered, and therefore which piece of quarkus-langchain4j instrumentation
 * observes it.
 *
 *   local @Tool  → ToolSpanWrapper           → six attributes, arguments + result
 *   MCP tool     → TracingMcpClientListener  → tool name, and no content at all
 *
 * Same protocol-independent operation, same data, two span shapes. Switch with
 * {@code AGENT_TOOLS=local|mcp} and diff the spans.
 */
@ApplicationScoped
public class CustomerLocalTools {

    @Inject
    CustomerDatabase db;

    @Inject
    CapybaraMetrics metrics;

    @Tool("List all customer records in the database.")
    public String list_records() {
        return db.listRecords().toString();
    }

    @Tool("Query customer records, optionally filtered by plan (e.g. 'free' or 'pro').")
    public String query(@P(value = "plan to filter by, or omit for all", required = false) String plan) {
        return db.query(blankToNull(plan)).toString();
    }

    @Tool("Delete customer records. With no plan, deletes ALL records. Destructive.")
    public String delete_records(@P(value = "plan whose records to delete; omit to delete ALL", required = false) String plan) {
        var result = db.deleteRecords(blankToNull(plan));
        // The application connects as app_svc, so that is the role the database saw.
        // Counting agent deletions under the same metric as the service account's is the point:
        // one graph, and the label says which of them did it.
        metrics.recordDeletion("app_svc", result.deleted());
        return result.toString();
    }

    @Tool("Recent changes to the customers table, newest first, with the client and database role that made each one. Use this to find out WHO changed something.")
    public String audit_log(@P(value = "how many entries to return; 20 is usually enough", required = false) Integer limit) {
        return db.auditLog(limit == null ? 20 : limit).toString();
    }

    /** The model sometimes sends "" rather than omitting the argument; both mean "all". */
    private static String blankToNull(String s) {
        return (s == null || s.isBlank()) ? null : s;
    }
}
