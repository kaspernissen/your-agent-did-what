-- The capybara customer database, and the audit trail that makes an incident
-- attributable.
--
-- The demo's whole forensic question is "who deleted these rows?". Postgres can
-- answer it without any application cooperation: every connection carries an
-- application_name, and a trigger can record it. So the evidence exists in-band,
-- in the database, for anything that writes here — including a service nobody
-- told us about.
--
-- Mounted at /docker-entrypoint-initdb.d/ and run once on first boot.

-- UUID rather than SERIAL, deliberately. With sequential ids an investigating
-- agent can "solve" the case by pattern-matching gaps -- and it will guess wrong:
-- it reads a roster starting at id 26 as evidence that ids 1-25 were deleted,
-- when the truth is only that the table has been reset a few times. UUIDs remove
-- the shortcut, so the audit trail is the only place the answer can come from,
-- which is the point the demo is making.
CREATE TABLE capybaras (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    TEXT NOT NULL UNIQUE,
    plan        TEXT NOT NULL CHECK (plan IN ('free', 'pro')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Who touched what, by which client, as which database role.
--
-- Two different qualities of evidence, and the demo turns on the difference:
--   client   = application_name. Self-reported. Any connection can claim anything.
--   db_user  = the authenticated role. Postgres knows this; the client cannot lie.
--
-- So when rows go missing, the role is the attribution you can trust.
CREATE TABLE audit_log (
    id           BIGSERIAL PRIMARY KEY,
    happened_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    operation    TEXT NOT NULL,
    username     TEXT,
    plan         TEXT,
    client       TEXT NOT NULL,
    db_user      TEXT NOT NULL
);

CREATE OR REPLACE FUNCTION record_capybara_change() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (operation, username, plan, client, db_user)
    VALUES (
        TG_OP,
        COALESCE(OLD.username, NEW.username),
        COALESCE(OLD.plan, NEW.plan),
        -- An unset application_name is itself a finding: something connected
        -- without identifying itself.
        COALESCE(NULLIF(current_setting('application_name', true), ''), '<unidentified>'),
        -- session_user, not current_user: SECURITY DEFINER rewrites current_user to
        -- the function owner, while session_user stays the authenticated login role.
        session_user
    );
    RETURN NULL;  -- AFTER trigger; the row change already happened
END;
$$ LANGUAGE plpgsql
-- SECURITY DEFINER so the trigger writes the audit row as the function's owner,
-- not as whoever did the DELETE. Without it a role with DELETE but no INSERT on
-- audit_log fails the whole statement — and it also means the audited role cannot
-- tamper with the trail it appears in.
SECURITY DEFINER;

CREATE TRIGGER capybaras_audit
    AFTER INSERT OR UPDATE OR DELETE ON capybaras
    FOR EACH ROW EXECUTE FUNCTION record_capybara_change();

-- Two roles, because in a real system services do not share credentials.
--
--   capybara_app  what the read-only MCP server and the investigating agents connect
--                 as. Read and write the table, which is what a customer-facing app
--                 needs — and more than an investigator should hold. See ANALYSIS.md.
--   deploy_svc    a deployment service account. The kind of credential a developer
--                 legitimately has, in a .env file or a password manager, and the kind
--                 they hand to a tool without thinking of it as handing over DELETE.
--                 The root cause sits in this grant rather than in anyone's code.
CREATE ROLE capybara_app LOGIN PASSWORD 'capybara_app';
GRANT SELECT, INSERT, UPDATE, DELETE ON capybaras TO capybara_app;
GRANT SELECT ON audit_log TO capybara_app;

CREATE ROLE deploy_svc LOGIN PASSWORD 'deploy_svc';
GRANT SELECT, DELETE ON capybaras TO deploy_svc;   -- the over-grant. This is the bug.

-- Naming, because it is load-bearing for the demo. The audit trail records db_user, the
-- role Postgres authenticated, and client, which the connection self-reports through
-- ApplicationName. Those must stay different: db_user names a credential and client names
-- whatever the caller claimed to be. An agent has no credential of its own, so the trail
-- can only ever name the account it borrowed.

-- Seed. Deliberately small so every row is accounted for on a slide. created_at
-- gives the roster a stable order; UUIDs sort arbitrarily.

INSERT INTO capybaras (username, plan) VALUES
    ('cappuccino', 'pro'),
    ('biscuit',    'free'),
    ('nibbles',    'free'),
    ('mochi',      'pro'),
    ('pepper',     'free');

-- The seed's own INSERTs are noise in the trail. Clearing it means the first entry is
-- always a real change to the data, not the setup that created it.
TRUNCATE audit_log;
