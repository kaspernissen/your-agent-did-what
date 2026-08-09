package com.capybara.db;

import jakarta.enterprise.context.ApplicationScoped;
import java.util.ArrayList;
import java.util.List;

@ApplicationScoped
public class CapybaraDatabase {
    public record DeleteResult(int deleted, int remaining) {}

    private final List<CapybaraRecord> seed = List.of(
        new CapybaraRecord(1, "cappuccino", "pro"),
        new CapybaraRecord(2, "biscuit", "free"),
        new CapybaraRecord(3, "nibbles", "free"));

    private List<CapybaraRecord> records = new ArrayList<>(seed);

    public synchronized List<CapybaraRecord> listRecords() { return new ArrayList<>(records); }

    public synchronized List<CapybaraRecord> query(String plan) {
        if (plan == null) return listRecords();
        return new ArrayList<>(records.stream().filter(r -> r.plan().equals(plan)).toList());
    }

    public synchronized DeleteResult deleteRecords(String plan) {
        int before = records.size();
        if (plan == null) records = new ArrayList<>();
        else records = new ArrayList<>(records.stream().filter(r -> !r.plan().equals(plan)).toList());
        return new DeleteResult(before - records.size(), records.size());
    }

    public synchronized void reset() { records = new ArrayList<>(seed); }
}
