package com.capybara.db;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CapybaraDatabaseTest {
    CapybaraDatabase db;

    @BeforeEach
    void setUp() { db = new CapybaraDatabase(); }

    @Test
    void seedsThreeRecords() {
        assertEquals(3, db.listRecords().size());
    }

    @Test
    void queryFiltersByPlan() {
        assertEquals(2, db.query("free").size());
        assertEquals(1, db.query("pro").size());
        assertEquals(3, db.query(null).size());
    }

    @Test
    void deleteFreeRemovesExactlyFreeRows() {
        CapybaraDatabase.DeleteResult r = db.deleteRecords("free");
        assertEquals(2, r.deleted());
        assertEquals(1, r.remaining());
        assertTrue(db.listRecords().stream().allMatch(rec -> rec.plan().equals("pro")));
        assertEquals(1, db.listRecords().get(0).id());
    }

    @Test
    void deleteAllEmptiesTheDatabase() {
        assertEquals(3, db.deleteRecords(null).deleted());
        assertEquals(0, db.listRecords().size());
    }
}
