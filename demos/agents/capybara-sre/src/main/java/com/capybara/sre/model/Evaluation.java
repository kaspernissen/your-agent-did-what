package com.capybara.sre.model;

/**
 * One judge verdict, as returned to the caller.
 *
 * The authoritative copy of this is the {@code gen_ai.evaluation.result} event on
 * the {@code invoke_agent} span — that is what the convention defines and what a
 * backend consumes. This record exists so the demo UI can show the verdict beside
 * the answer without anyone having to open a trace viewer mid-talk.
 *
 * Exactly one of {@code score} or {@code label} is set, which is the shape the
 * convention describes: {@code score.value} for a metric, {@code score.label} for
 * a gate.
 */
public record Evaluation(String name, Double score, String label, String explanation) {}
