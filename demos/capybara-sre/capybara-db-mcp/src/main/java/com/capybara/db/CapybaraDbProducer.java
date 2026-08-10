package com.capybara.db;

import com.capybara.db.CapybaraDatabase;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;

/**
 * Produces the shared {@link CapybaraDatabase} as a bean.
 *
 * The class itself lives in capybara-db-core with no CDI annotations, so each
 * application declares its own instance here. Both tool paths therefore run
 * identical code over identical seed data.
 */
public class CapybaraDbProducer {

    @Produces
    @ApplicationScoped
    CapybaraDatabase capybaraDatabase() {
        return new CapybaraDatabase();
    }
}
