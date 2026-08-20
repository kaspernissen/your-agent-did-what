package com.customerdb;

import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.SpanKind;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Context;
import io.opentelemetry.context.Scope;
import io.opentelemetry.context.propagation.TextMapGetter;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.context.propagation.TextMapPropagator;
import io.quarkiverse.mcp.server.Meta;
import io.quarkiverse.mcp.server.MetaKey;
import io.quarkiverse.mcp.server.Tool;
import io.quarkiverse.mcp.server.ToolArg;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import jakarta.enterprise.context.ApplicationScoped;

/**
 * The four tools this server exposes, and the workaround that puts their work back in
 * the caller's trace.
 *
 * <h2>Why these methods open a span by hand</h2>
 *
 * quarkus-mcp-server creates a correctly parented span for the MCP request itself, so
 * {@code tools/call audit_log} lands in the agent's trace. The tool <em>body</em> then runs
 * on a fresh duplicated Vert.x context with no OpenTelemetry context at all, so everything it
 * does — the connection, the SQL — starts a new trace. That is
 * quarkiverse/quarkus-mcp-server#789, open since May.
 *
 * Proven rather than assumed: annotating a method with {@code @WithSpan} produces a span with
 * no parent. A stale-but-present context would have produced a child.
 *
 * The fix does not need the framework, because MCP already carries what we need. Trace context
 * travels in the request's {@code _meta} under the unprefixed {@code traceparent} key, which is
 * what SEP-414 reserves it for, and {@link Meta} hands that map to the tool. So we extract the
 * caller's context ourselves and start the span against it. The SQL then nests underneath and the
 * whole tool call is one trace again.
 *
 * Delete this and the demo shows the gap; keep it and the demo shows the gap and the way out.
 */
@ApplicationScoped
public class CustomerDbTools {

    @Inject CustomerDatabase db;
    @Inject Tracer tracer;
    @Inject OpenTelemetry openTelemetry;

    /**
     * Off shows the gap, on shows the fix, and the talk needs both. With this false the tool body
     * runs exactly as quarkus-mcp-server leaves it and the SQL starts its own trace.
     */
    @ConfigProperty(name = "mcp.propagate-context", defaultValue = "true")
    boolean propagateContext;

    /** Reads a single header out of the _meta map the MCP client sent. */
    private static final TextMapGetter<Meta> META_GETTER = new TextMapGetter<>() {
        @Override public Iterable<String> keys(Meta meta) {
            return meta.asJsonObject() == null ? java.util.List.of() : meta.asJsonObject().fieldNames();
        }
        @Override public String get(Meta meta, String key) {
            if (meta == null) return null;
            Object v = meta.getValue(MetaKey.of(key));
            return v == null ? null : v.toString();
        }
    };

    /**
     * Runs the tool body inside a span parented to whoever called us over MCP.
     *
     * Falls back to the ambient context when _meta carries no traceparent, which keeps a plain
     * client working; it just gets the orphaned trace it would have had anyway.
     */
    private <T> T inCallerTrace(String toolName, Meta meta, java.util.function.Supplier<T> body) {
        if (!propagateContext) {
            return body.get();
        }
        Context parent = meta == null ? Context.current()
                : openTelemetry.getPropagators().getTextMapPropagator()
                        .extract(Context.root(), meta, META_GETTER);
        Span span = tracer.spanBuilder("execute_tool " + toolName)
                .setSpanKind(SpanKind.INTERNAL)
                .setParent(parent)
                .setAttribute("gen_ai.operation.name", "execute_tool")
                .setAttribute("gen_ai.tool.name", toolName)
                .startSpan();
        try (Scope ignored = span.makeCurrent()) {
            return body.get();
        } catch (RuntimeException e) {
            span.recordException(e);
            throw e;
        } finally {
            span.end();
        }
    }

    @Tool(name = "list_records", description = "List all capybara customer records in the database.")
    public String listRecords(Meta meta) {
        return inCallerTrace("list_records", meta, () -> db.listRecords().toString());
    }

    @Tool(name = "query", description = "Query customer records, optionally filtered by plan (e.g. 'free' or 'pro').")
    public String query(@ToolArg(description = "plan to filter by, or omit for all") String plan, Meta meta) {
        return inCallerTrace("query", meta, () -> db.query(plan).toString());
    }

    @Tool(name = "delete_records", description = "Delete customer records. With no plan, deletes ALL records. Destructive.")
    public String deleteRecords(@ToolArg(description = "plan whose records to delete; omit to delete ALL") String plan, Meta meta) {
        return inCallerTrace("delete_records", meta, () -> db.deleteRecords(plan).toString());
    }

    @Tool(name = "audit_log", description = "Recent changes to the customers table, newest first, with the client and database role that made each one. Use this to find out WHO changed something.")
    public String auditLog(@ToolArg(description = "how many entries to return; 20 is usually enough") Integer limit, Meta meta) {
        return inCallerTrace("audit_log", meta, () -> db.auditLog(limit == null ? 20 : limit).toString());
    }
}
