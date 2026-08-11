package com.capybara.db;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * The capybara database, in Postgres.
 *
 * Plain JDBC on purpose: {@code java.sql} and {@code javax.sql} are in the JDK, so
 * this module still has no external dependencies and both applications can share it
 * without either dragging a persistence framework into the other.
 *
 * The {@link DataSource} is supplied by whichever application produces this bean,
 * which is also what makes the tool calls show up as SQL spans — the container
 * instruments the datasource, and this class is deliberately too boring to
 * interfere with that.
 */
public class JdbcCapybaraDatabase implements CapybaraDatabase {

    private final DataSource dataSource;

    public JdbcCapybaraDatabase(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public List<CapybaraRecord> listRecords() {
        return select("SELECT id, username, plan FROM capybaras ORDER BY created_at, username", null);
    }

    @Override
    public List<CapybaraRecord> query(String plan) {
        if (plan == null) return listRecords();
        return select("SELECT id, username, plan FROM capybaras WHERE plan = ? ORDER BY created_at, username", plan);
    }

    @Override
    public DeleteResult deleteRecords(String plan) {
        String sql = plan == null
                ? "DELETE FROM capybaras"
                : "DELETE FROM capybaras WHERE plan = ?";
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(sql)) {
            if (plan != null) ps.setString(1, plan);
            int deleted = ps.executeUpdate();
            return new DeleteResult(deleted, count(c));
        } catch (SQLException e) {
            throw new IllegalStateException("delete failed: " + e.getMessage(), e);
        }
    }

    /**
     * The audit trail, newest first.
     *
     * This is the tool that answers "who did this?". The rows come from a trigger,
     * so anything that writes to the table appears here whether or not it wanted to.
     */
    @Override
    public List<AuditEntry> auditLog(int limit) {
        String sql = """
                SELECT to_char(happened_at, 'HH24:MI:SS') AS at,
                       operation, username, plan, client, db_user
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?""";
        List<AuditEntry> out = new ArrayList<>();
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setInt(1, Math.max(1, Math.min(limit, 200)));
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(new AuditEntry(
                            rs.getString("at"),
                            rs.getString("operation"),
                            rs.getString("username"),
                            rs.getString("plan"),
                            // Two columns, one field: the role is the trustworthy half,
                            // so show both and let the reader see the difference.
                            rs.getString("client") + " (db role: " + rs.getString("db_user") + ")"));
                }
            }
        } catch (SQLException e) {
            throw new IllegalStateException("audit query failed: " + e.getMessage(), e);
        }
        return out;
    }

    private List<CapybaraRecord> select(String sql, String arg) {
        List<CapybaraRecord> out = new ArrayList<>();
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(sql)) {
            if (arg != null) ps.setString(1, arg);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(new CapybaraRecord(rs.getString("id"), rs.getString("username"), rs.getString("plan")));
                }
            }
        } catch (SQLException e) {
            throw new IllegalStateException("query failed: " + e.getMessage(), e);
        }
        return out;
    }

    private static int count(Connection c) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement("SELECT count(*) FROM capybaras");
             ResultSet rs = ps.executeQuery()) {
            return rs.next() ? rs.getInt(1) : 0;
        }
    }

}
