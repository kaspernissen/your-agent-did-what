package com.capybara.db;

import io.quarkiverse.mcp.server.Tool;
import io.quarkiverse.mcp.server.ToolArg;
import jakarta.inject.Inject;
import jakarta.enterprise.context.ApplicationScoped;

@ApplicationScoped
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

    @Tool(name = "audit_log", description = "Recent changes to the capybaras table, newest first, with the client and database role that made each one. Use this to find out WHO changed something.")
    public String auditLog(@ToolArg(description = "how many entries to return; 20 is usually enough") Integer limit) {
        return db.auditLog(limit == null ? 20 : limit).toString();
    }
}
