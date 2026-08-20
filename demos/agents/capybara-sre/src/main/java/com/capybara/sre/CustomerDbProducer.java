package com.capybara.sre;

import com.customerdb.CustomerDatabase;
import com.customerdb.JdbcCustomerDatabase;
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
public class CustomerDbProducer {

    @Inject
    DataSource dataSource;

    @Produces
    @ApplicationScoped
    CustomerDatabase capybaraDatabase() {
        return new JdbcCustomerDatabase(dataSource);
    }
}
