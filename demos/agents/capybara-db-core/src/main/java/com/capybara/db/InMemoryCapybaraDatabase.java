package com.capybara.db;

import java.util.ArrayList;
import java.util.List;

/**
 * The capybara database in memory, for tests.
 *
 * Keeps the unit tests hermetic — no container, no connection, no cleanup. It has
 * no audit trail, because the audit trail is a Postgres trigger and inventing a
 * fake one here would let a test pass that the real database would fail.
 */
public class InMemoryCapybaraDatabase implements CapybaraDatabase {

    // Fixed ids, so a test can assert on one. Real rows get a gen_random_uuid()
    // from Postgres; these only need to be well-formed and stable.
    private static final String ID = "00000000-0000-4000-8000-00000000000";

    private final List<CapybaraRecord> seed = List.of(
        new CapybaraRecord(ID + "1", "cappuccino", "pro"),
        new CapybaraRecord(ID + "2", "biscuit", "free"),
        new CapybaraRecord(ID + "3", "nibbles", "free"),
        new CapybaraRecord(ID + "4", "mochi", "pro"),
        new CapybaraRecord(ID + "5", "pepper", "free"));

    private List<CapybaraRecord> records = new ArrayList<>(seed);

    @Override
    public synchronized List<CapybaraRecord> listRecords() { return new ArrayList<>(records); }

    @Override
    public synchronized List<CapybaraRecord> query(String plan) {
        if (plan == null) return listRecords();
        return new ArrayList<>(records.stream().filter(r -> r.plan().equals(plan)).toList());
    }

    @Override
    public synchronized DeleteResult deleteRecords(String plan) {
        int before = records.size();
        if (plan == null) records = new ArrayList<>();
        else records = new ArrayList<>(records.stream().filter(r -> !r.plan().equals(plan)).toList());
        return new DeleteResult(before - records.size(), records.size());
    }

    @Override
    public synchronized List<AuditEntry> auditLog(int limit) { return List.of(); }

    /** Not part of the interface — tests use it to start from the seed. */
    public synchronized void restoreSeed() { records = new ArrayList<>(seed); }
}
