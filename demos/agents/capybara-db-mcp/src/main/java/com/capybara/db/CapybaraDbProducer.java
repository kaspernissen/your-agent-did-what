package com.capybara.db;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;

import javax.sql.DataSource;

/**
 * Produces the database the MCP tools talk to — the same Postgres the agent uses.
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
