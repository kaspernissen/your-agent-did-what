package com.capybara.sre;

import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;

/**
 * A thin pass-through to demo 2's convention agents, so one console can trigger both
 * demos.
 *
 * The browser cannot call those services directly -- they live inside the cluster, and
 * a console served from this origin would need a port-forward per variant plus a
 * hardcoded localhost port to reach them. Proxying keeps the console a single URL with
 * nothing to set up.
 *
 * This is the only coupling between the two demos, and it is one-directional and
 * optional: demo 2 does not know this exists, and if it is not deployed the endpoint
 * returns a message the console can show rather than failing.
 */
@Path("/conventions")
@Produces(MediaType.APPLICATION_JSON)
public class ConventionResource {

    private static final Logger LOG = Logger.getLogger(ConventionResource.class);

    /** Runs take as long as an agent loop with tool calls, so this is generous. */
    private static final Duration TIMEOUT = Duration.ofSeconds(120);

    @ConfigProperty(name = "capybara.conventions.openinference",
                    defaultValue = "http://convention-openinference:8000")
    String openinferenceUrl;

    @ConfigProperty(name = "capybara.conventions.openlit",
                    defaultValue = "http://convention-openlit:8000")
    String openlitUrl;

    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

    @POST
    @Path("/{variant}")
    public Response run(@PathParam("variant") String variant) {
        String base = switch (variant) {
            case "openinference" -> openinferenceUrl;
            case "openlit" -> openlitUrl;
            default -> null;
        };
        if (base == null) {
            return Response.status(400)
                    .entity(Map.of("error", "unknown variant '" + variant + "'")).build();
        }

        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(base + "/run"))
                    .header("Content-Type", MediaType.APPLICATION_JSON)
                    .timeout(TIMEOUT)
                    .POST(HttpRequest.BodyPublishers.ofString("{}"))
                    .build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            // Pass the body through untouched: demo 2 owns that shape, and re-modelling
            // it here would be a second place to keep in sync.
            return Response.status(response.statusCode())
                    .type(MediaType.APPLICATION_JSON)
                    .entity(response.body())
                    .build();
        } catch (Exception e) {
            LOG.warnf("convention agent '%s' unreachable at %s: %s", variant, base, e.getMessage());
            return Response.status(503).entity(Map.of(
                    "error", "The " + variant + " agent is not reachable. Deploy demo 2: demos/demo-2/deploy.sh",
                    "detail", e.getClass().getSimpleName() + ": " + e.getMessage())).build();
        }
    }
}
