package com.customerdb;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The tool behaviour, against the in-memory database.
 *
 * Assertions are derived from the seed rather than hard-coded counts, so growing
 * the roster does not silently turn these red — which is exactly what happened when
 * it went from three customers to five.
 */
class CustomerDatabaseTest {

    private static final int FREE = 3;   // biscuit, nibbles, pepper
    private static final int PRO  = 2;   // cappuccino, mochi

    CustomerDatabase db;

    @BeforeEach
    void setUp() {
        db = new InMemoryCustomerDatabase();
    }

    @Test
    void seedsTheDemoRoster() {
        assertEquals(FREE + PRO, db.listRecords().size());
    }

    @Test
    void queryFiltersByPlan() {
        assertEquals(FREE, db.query("free").size());
        assertEquals(PRO, db.query("pro").size());
        assertEquals(FREE + PRO, db.query(null).size());
    }

    @Test
    void deleteFreeRemovesExactlyFreeRows() {
        CustomerDatabase.DeleteResult r = db.deleteRecords("free");
        assertEquals(FREE, r.deleted());
        assertEquals(PRO, r.remaining());
        assertTrue(db.listRecords().stream().allMatch(rec -> rec.plan().equals("pro")));
    }

    @Test
    void deleteAllEmptiesTheDatabase() {
        assertEquals(FREE + PRO, db.deleteRecords(null).deleted());
        assertEquals(0, db.listRecords().size());
    }

    @Test
    void inMemoryHasNoAuditTrail() {
        // The trail is a Postgres trigger. Faking one here would let a test pass that
        // the real database fails, so it stays empty and the demo proves it for real.
        assertTrue(db.auditLog(20).isEmpty());
    }
}
