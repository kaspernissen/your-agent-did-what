package com.capybara.sre;

import com.capybara.sre.model.Evaluation;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.logs.LogRecordBuilder;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.context.Context;

import java.time.Instant;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.util.ArrayList;
import java.util.List;
import org.jboss.logging.Logger;

/**
 * Emits {@code gen_ai.evaluation.result} events for the judge's verdicts.
 *
 * These are Events in the OpenTelemetry <em>logs</em> data model -- log records
 * carrying an event name -- which is what the convention asks for. It is worth being
 * precise about this, because three different things get called "events" here and only
 * one of them is the spec's: OTel log-record Events, span events, and the tab Jaeger
 * labels "Logs" that actually shows span events. This class emits the first.
 *
 * Attribute shape per open-telemetry/semantic-conventions-genai,
 * docs/gen-ai/gen-ai-events.md (verified 2026-08-11):
 *
 *   gen_ai.evaluation.name         Required
 *   gen_ai.evaluation.score.value  Conditionally Required (double)
 *   gen_ai.evaluation.score.label  Conditionally Required (string)
 *   gen_ai.evaluation.explanation  Recommended
 *   gen_ai.response.id             Recommended
 *   error.type                     Conditionally Required — when the evaluation itself failed
 *
 * The spec says the event SHOULD be parented to the GenAI operation span being
 * evaluated, or else carry gen_ai.response.id when the span id is not available. We
 * have the span, so each record is emitted in a Context carrying it and correlates by
 * trace and span id -- no response id needed. The span is never made current in the
 * request thread, so that Context has to be built explicitly rather than inherited.
 *
 * NOTE FOR THE TALK: judging in-process and synchronously is NOT how you would
 * do this in production — real setups evaluate offline against stored traces.
 * We do it here because it makes parenting trivially correct and removes a
 * container, and we say so on the slide rather than implying otherwise.
 */
@ApplicationScoped
public class EvaluationEmitter {

    private static final Logger LOG = Logger.getLogger(EvaluationEmitter.class);
    private static final String EVENT = "gen_ai.evaluation.result";

    private static final AttributeKey<String> NAME = AttributeKey.stringKey("gen_ai.evaluation.name");
    private static final AttributeKey<Double> SCORE = AttributeKey.doubleKey("gen_ai.evaluation.score.value");
    private static final AttributeKey<String> LABEL = AttributeKey.stringKey("gen_ai.evaluation.score.label");
    private static final AttributeKey<String> WHY = AttributeKey.stringKey("gen_ai.evaluation.explanation");
    private static final AttributeKey<String> ERROR = AttributeKey.stringKey("error.type");

    private final io.opentelemetry.api.logs.Logger events =
            GlobalOpenTelemetry.get().getLogsBridge().get("com.capybara.sre.evaluation");

    /**
     * One log record, named and correlated to the span under evaluation.
     *
     * Every emitter below goes through here, so the event name and the correlation
     * cannot be got right in one place and wrong in another.
     */
    private LogRecordBuilder event(Span span, String name) {
        return events.logRecordBuilder()
                .setEventName(EVENT)
                // Without an explicit timestamp the record carries epoch 0. Some backends
                // fall back to ObservedTimestamp and it looks fine; others file the verdict
                // in 1970, where nobody will find it.
                .setTimestamp(Instant.now())
                .setContext(Context.current().with(span))
                .setAttribute(NAME, name);
    }

    @Inject
    ObjectMapper objectMapper;

    /**
     * Parse the judge's JSON, attach one event per dimension, and return the
     * verdicts so the caller can show them.
     *
     * The span events are the authoritative output — this return value is a
     * convenience for the demo UI, not a second source of truth.
     */
    public List<Evaluation> emit(Span span, String judgeJson) {
        List<Evaluation> out = new ArrayList<>();
        try {
            String cleaned = stripFence(judgeJson);
            JsonNode root = objectMapper.readTree(cleaned);
            out.add(emitScored(span, "root_cause_correctness", root.path("root_cause_correctness")));
            out.add(emitLabelled(span, "remediation_safety", root.path("remediation_safety")));
        } catch (Exception e) {
            // A judge failure must never fail the investigation. Emit the error
            // shape instead: the Required name, plus error.type, and no score.
            // Log what actually arrived, bounded. Without it the only evidence is a
            // Jackson message that says the JSON ended early but not what it contained,
            // and the cause -- a truncated reply versus a chatty preamble -- is a guess.
            String seen = judgeJson == null ? "<null>" : judgeJson;
            LOG.warnf(e, "judge output unparseable (%d chars): %s", seen.length(),
                    seen.length() > 400 ? seen.substring(0, 400) + "..." : seen);
            emitError(span, "root_cause_correctness", e);
            emitError(span, "remediation_safety", e);
        }
        return out;
    }

    /** The evaluation errored before producing any result at all. */
    public void emitFailure(Span span, Throwable t) {
        emitError(span, "root_cause_correctness", t);
        emitError(span, "remediation_safety", t);
    }

    private Evaluation emitScored(Span span, String name, JsonNode node) {
        double score = node.path("score").asDouble();
        LogRecordBuilder b = event(span, name).setAttribute(SCORE, score);
        putExplanation(b, node);
        b.emit();
        return new Evaluation(name, score, null, node.path("explanation").asText(""));
    }

    private Evaluation emitLabelled(Span span, String name, JsonNode node) {
        String label = node.path("label").asText("unknown");
        LogRecordBuilder b = event(span, name).setAttribute(LABEL, label);
        putExplanation(b, node);
        b.emit();
        return new Evaluation(name, null, label, node.path("explanation").asText(""));
    }

    private void putExplanation(LogRecordBuilder b, JsonNode node) {
        String explanation = node.path("explanation").asText("");
        if (!explanation.isBlank()) {
            b.setAttribute(WHY, explanation);
        }
    }

    private void emitError(Span span, String name, Throwable t) {
        event(span, name).setAttribute(ERROR, t.getClass().getName()).emit();
    }

    /** Models like wrapping JSON in ```json fences; the spec does not. */
    private String stripFence(String s) {
        String t = s.trim();
        if (t.startsWith("```")) {
            int nl = t.indexOf('\n');
            if (nl > 0) t = t.substring(nl + 1);
            if (t.endsWith("```")) t = t.substring(0, t.length() - 3);
        }
        return t.trim();
    }
}
