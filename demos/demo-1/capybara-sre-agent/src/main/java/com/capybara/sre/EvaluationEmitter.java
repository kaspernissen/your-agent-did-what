package com.capybara.sre;

import com.capybara.sre.model.Evaluation;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.common.AttributesBuilder;
import io.opentelemetry.api.trace.Span;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.util.ArrayList;
import java.util.List;
import org.jboss.logging.Logger;

/**
 * Emits {@code gen_ai.evaluation.result} events onto the GenAI operation span.
 *
 * Attribute shape per open-telemetry/semantic-conventions-genai,
 * docs/gen-ai/gen-ai-events.md (verified 2026-08-07):
 *
 *   gen_ai.evaluation.name         Required
 *   gen_ai.evaluation.score.value  Conditionally Required (double)
 *   gen_ai.evaluation.score.label  Conditionally Required (string)
 *   gen_ai.evaluation.explanation  Recommended
 *   gen_ai.response.id             Recommended
 *   error.type                     Conditionally Required — when the evaluation itself failed
 *
 * The spec says the event SHOULD be parented to the GenAI operation span being
 * evaluated. We add it directly to the live invoke_agent span before it ends,
 * which satisfies that without needing gen_ai.response.id for correlation.
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
            LOG.warnf(e, "judge output unparseable, emitting error events");
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
        AttributesBuilder b = Attributes.builder()
                .put("gen_ai.evaluation.name", name)
                .put("gen_ai.evaluation.score.value", score);
        putExplanation(b, node);
        span.addEvent(EVENT, b.build());
        return new Evaluation(name, score, null, node.path("explanation").asText(""));
    }

    private Evaluation emitLabelled(Span span, String name, JsonNode node) {
        String label = node.path("label").asText("unknown");
        AttributesBuilder b = Attributes.builder()
                .put("gen_ai.evaluation.name", name)
                .put("gen_ai.evaluation.score.label", label);
        putExplanation(b, node);
        span.addEvent(EVENT, b.build());
        return new Evaluation(name, null, label, node.path("explanation").asText(""));
    }

    private void putExplanation(AttributesBuilder b, JsonNode node) {
        String explanation = node.path("explanation").asText("");
        if (!explanation.isBlank()) {
            b.put("gen_ai.evaluation.explanation", explanation);
        }
    }

    private void emitError(Span span, String name, Throwable t) {
        span.addEvent(EVENT, Attributes.builder()
                .put("gen_ai.evaluation.name", name)
                .put("error.type", t.getClass().getName())
                .build());
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
