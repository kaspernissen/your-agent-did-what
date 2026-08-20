package com.customerdb;

import java.util.List;

/**
 * The customer database, as the tools see it.
 *
 * An interface so the same three tool implementations can run against real
 * Postgres in the demo and against memory in tests, without the tools — or the
 * agent above them — knowing which. {@link JdbcCustomerDatabase} is the real one;
 * {@link InMemoryCustomerDatabase} keeps the unit tests hermetic.
 */
public interface CustomerDatabase {

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

    List<CustomerRecord> listRecords();

    List<CustomerRecord> query(String plan);

    DeleteResult deleteRecords(String plan);

    /** The most recent changes, newest first. Empty if nothing has happened. */
    List<AuditEntry> auditLog(int limit);
}
