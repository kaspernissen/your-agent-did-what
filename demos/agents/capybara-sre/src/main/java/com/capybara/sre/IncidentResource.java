package com.capybara.sre;

import com.customerdb.CustomerDatabase;
import io.quarkus.agroal.DataSource;
import jakarta.inject.Inject;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.jboss.logging.Logger;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.Map;

/**
 * Stage controls: put the database back, and rehearse the deletion without a model.
 *
 * <h2>Why a rehearsal endpoint exists at all</h2>
 *
 * The incident is caused by a coding agent. A developer asks goose to tidy up the free
 * plan, goose calls {@code delete_records} on {@code prod-db-mcp}, and that server is
 * holding {@code deploy_svc} credentials which carry DELETE. See
 * {@code agents/goose/run-recipe.sh}; that is the real path and the one to demo.
 *
 * It needs ollama and a local model, which a conference network cannot be relied on to
 * make available. So this endpoint reproduces the database state that run leaves behind:
 * it connects with the same {@code deploy_svc} credentials and issues the same DELETE.
 *
 * Two honest caveats, because a stand-in that is mistaken for the real thing is worse
 * than no stand-in. It produces no agent telemetry, so nothing in the trace explains
 * <em>why</em> the rows went — which is exactly the evidence the talk is about. And the
 * {@code client} column will read {@code goose} because this connection says so through
 * ApplicationName, which is a self-reported label rather than an authenticated fact. That
 * is true of the real run too, and it is the point: {@code db_user} is the only column
 * Postgres vouches for.
 *
 * What is not faked either way is the root cause. {@code deploy_svc} can do this because
 * it was granted DELETE on a table it has no business deleting from — see
 * {@code postgres/init.sql}. That grant is the bug, and it is what a good diagnosis names.
 */
@Path("/incident")
public class IncidentResource {

    private static final Logger LOG = Logger.getLogger(IncidentResource.class);

    /** The service account's own credentials, so the audit trail attributes this correctly. */
    @Inject
    @DataSource("deploy")
    javax.sql.DataSource deployDataSource;

    @Inject
    CapybaraMetrics metrics;

    /** Maintenance credentials. Clearing the audit trail is deliberately not a
     *  privilege the application role holds. */
    @Inject
    @DataSource("admin")
    javax.sql.DataSource adminDataSource;

    @Inject
    CustomerDatabase db;

    @POST
    @Path("/rehearse-deletion")
    @Produces(MediaType.APPLICATION_JSON)
    public Map<String, Object> rehearseDeletion() {
        try (Connection c = deployDataSource.getConnection();
             PreparedStatement ps = c.prepareStatement("DELETE FROM customers WHERE plan = 'free'")) {
            int deleted = ps.executeUpdate();
            // Attributed to the role, not to the client name the connection claims.
            metrics.recordDeletion("deploy_svc", deleted);
            LOG.warnf("rehearsal: deleted %d free-plan customers as deploy_svc", deleted);
            return Map.of("deleted", deleted,
                          "by", "goose (db role: deploy_svc)",
                          "remaining", db.listRecords().size());
        } catch (SQLException e) {
            LOG.error("rehearsal deletion failed", e);
            return Map.of("error", e.getMessage());
        }
    }

    @POST
    @Path("/reset")
    @Produces(MediaType.APPLICATION_JSON)
    public Map<String, Object> reset() {
        try (Connection c = adminDataSource.getConnection()) {
            exec(c, "DELETE FROM customers");
            exec(c, """
                    INSERT INTO customers (username, plan) VALUES
                        ('cappuccino','pro'), ('biscuit','free'), ('nibbles','free'),
                        ('mochi','pro'), ('pepper','free')""");
            // Last, so restoring the seed is not itself the first thing in the trail.
            exec(c, "DELETE FROM audit_log");
            return Map.of("records", db.listRecords().size(), "audit", db.auditLog(50).size());
        } catch (SQLException e) {
            LOG.error("reset failed", e);
            return Map.of("error", e.getMessage());
        }
    }

    private static void exec(Connection c, String sql) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.execute();
        }
    }
}
