package com.capybara.sre;

import com.capybara.db.CapybaraDatabase;
import com.capybara.db.JdbcCapybaraDatabase;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;

import javax.sql.DataSource;

/**
 * Produces the database the tools talk to.
 *
 * Both tool paths — local {@code @Tool} methods and the MCP server — end up on this
 * same Postgres instance, so the beat-4 comparison no longer has to caveat that
 * each side kept its own copy of the data.
 */
public class CapybaraDbProducer {

    @Inject
    DataSource dataSource;

    @Produces
    @ApplicationScoped
    CapybaraDatabase capybaraDatabase() {
        return new JdbcCapybaraDatabase(dataSource);
    }
}
