package com.capybara.sre;

import com.capybara.db.CapybaraDatabase;
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.Meter;
import io.quarkus.runtime.StartupEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import jakarta.inject.Inject;
import org.jboss.logging.Logger;

/**
 * Two metrics, so the incident is visible without reading a single trace.
 *
 * <ul>
 *   <li>{@code capybara.records} -- how many customers exist right now. On a graph this
 *       is the whole story: a flat line at five that drops to two.</li>
 *   <li>{@code capybara.records.deleted} -- a counter, labelled with the database role
 *       that did it. This is the metric that distinguishes "rows went missing" from
 *       "the kangaroo role deleted them", which is the same distinction the audit trail
 *       makes, one signal earlier.</li>
 * </ul>
 *
 * The gauge is observable: it reads the count when the SDK collects, rather than being
 * updated from the write paths. That way it cannot drift out of step with the database
 * if something deletes rows without telling us -- which is precisely the scenario.
 */
@ApplicationScoped
public class CapybaraMetrics {

    private static final Logger LOG = Logger.getLogger(CapybaraMetrics.class);

    /** The authenticated role, not the self-reported client name. Same reasoning as the audit trail. */
    private static final AttributeKey<String> ACTOR = AttributeKey.stringKey("capybara.actor.db_user");

    @Inject
    CapybaraDatabase database;

    private io.opentelemetry.api.metrics.LongCounter deleted;

    /**
     * Registered on startup rather than in a @PostConstruct.
     *
     * An @ApplicationScoped bean is injected as a proxy, so being injected somewhere is
     * not enough to construct it -- @PostConstruct would not run until something first
     * called a method. The gauge would then be missing until the first deletion, which is
     * exactly when you want it already reporting.
     */
    void register(@Observes StartupEvent ignored) {
        Meter meter = GlobalOpenTelemetry.get().getMeter("com.capybara.sre");

        deleted = meter.counterBuilder("capybara.records.deleted")
                .setDescription("Customer records deleted, by the database role that deleted them")
                .setUnit("{record}")
                .build();

        meter.gaugeBuilder("capybara.records")
                .ofLongs()
                .setDescription("Customer records currently in the database")
                .setUnit("{record}")
                .buildWithCallback(observation -> {
                    try {
                        observation.record(database.listRecords().size());
                    } catch (Exception e) {
                        // A metrics callback must never throw: the SDK would drop the whole
                        // collection cycle, and a database blip would look like an outage.
                        LOG.debugf("record count unavailable: %s", e.getMessage());
                    }
                });
    }

    /** Record a deletion against the role that performed it. */
    public void recordDeletion(String dbUser, long count) {
        if (count > 0) {
            deleted.add(count, Attributes.of(ACTOR, dbUser));
        }
    }
}
