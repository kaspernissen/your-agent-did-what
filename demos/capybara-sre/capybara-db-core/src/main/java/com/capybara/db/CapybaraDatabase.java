package com.capybara.db;

import java.util.List;

/**
 * The capybara customer database, as the tools see it.
 *
 * An interface so the same three tool implementations can run against real
 * Postgres in the demo and against memory in tests, without the tools — or the
 * agent above them — knowing which. {@link JdbcCapybaraDatabase} is the real one;
 * {@link InMemoryCapybaraDatabase} keeps the unit tests hermetic.
 */
public interface CapybaraDatabase {

    /** How many rows a delete removed, and how many are left. */
    record DeleteResult(int deleted, int remaining) {}

    /**
     * One recorded change to the table, and which client made it.
     *
     * This is the demo's forensic payload: Postgres records the connection's
     * application_name, so a service that writes here identifies itself whether or
     * not anyone instrumented it.
     */
    record AuditEntry(String at, String operation, String username, String plan, String client) {}

    List<CapybaraRecord> listRecords();

    List<CapybaraRecord> query(String plan);

    DeleteResult deleteRecords(String plan);

    /** The most recent changes, newest first. Empty if nothing has happened. */
    List<AuditEntry> auditLog(int limit);

    /** Restore the seed, and clear the audit trail. Used between demo runs. */
    void reset();
}
