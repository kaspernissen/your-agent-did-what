package com.capybara.sre;

import com.capybara.db.CapybaraDatabase;
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
 * Stage controls: cause the incident, and put things back.
 *
 * <h2>What the kangaroo is, honestly</h2>
 *
 * A neighbouring team's service connected straight to the capybara database and
 * deleted rows. This endpoint stands in for that service: it connects using the
 * {@code kangaroo} role's own credentials and issues the DELETE the way that service
 * would.
 *
 * It is a fault injector living in the agent's process, not a separate deployment —
 * that keeps the demo to one binary. What is <em>not</em> faked is the part the
 * investigation depends on: the connection authenticates as {@code kangaroo}, so
 * Postgres records the deletion against that role, and the agent has to discover it
 * from the audit trail like it would any other client.
 *
 * The root cause is real too. {@code kangaroo} can do this because it was granted
 * DELETE on a table it has no business deleting from — see {@code postgres/init.sql}.
 * That grant is the bug, and it is the thing a good diagnosis should name.
 */
@Path("/incident")
public class IncidentResource {

    private static final Logger LOG = Logger.getLogger(IncidentResource.class);

    /** The kangaroo's own credentials, so the audit trail attributes this correctly. */
    @Inject
    @DataSource("kangaroo")
    javax.sql.DataSource kangarooDataSource;

    /** Maintenance credentials. Clearing the audit trail is deliberately not a
     *  privilege the application role holds. */
    @Inject
    @DataSource("admin")
    javax.sql.DataSource adminDataSource;

    @Inject
    CapybaraDatabase db;

    @POST
    @Path("/kangaroo")
    @Produces(MediaType.APPLICATION_JSON)
    public Map<String, Object> kangarooRampage() {
        try (Connection c = kangarooDataSource.getConnection();
             PreparedStatement ps = c.prepareStatement("DELETE FROM capybaras WHERE plan = 'free'")) {
            int deleted = ps.executeUpdate();
            LOG.warnf("kangaroo-service deleted %d free-plan capybaras", deleted);
            return Map.of("deleted", deleted,
                          "by", "kangaroo-service (db role: kangaroo)",
                          "remaining", db.listRecords().size());
        } catch (SQLException e) {
            LOG.error("kangaroo rampage failed", e);
            return Map.of("error", e.getMessage());
        }
    }

    @POST
    @Path("/reset")
    @Produces(MediaType.APPLICATION_JSON)
    public Map<String, Object> reset() {
        try (Connection c = adminDataSource.getConnection()) {
            exec(c, "DELETE FROM capybaras");
            exec(c, """
                    INSERT INTO capybaras (username, plan) VALUES
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
