package com.capybara.db;

/**
 * One customer row.
 *
 * The id is a UUID string rather than a number so that nothing downstream can infer
 * history from it. An agent handed sequential ids will reason about the gaps between
 * them and reach confident, wrong conclusions; the audit trail is the only honest
 * source for what happened to a row.
 */
public record CapybaraRecord(String id, String user, String plan) {}
