package com.capybara.sre;

import com.capybara.sre.model.ChatRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
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
 * A thin pass-through to the two Python SRE agents, beaver-sre and otter-sre -- the same
 * job on a different platform.
 *
 * The browser cannot call them directly -- they live inside the cluster, and a console
 * served from this origin would need a port-forward plus a hardcoded localhost port to
 * reach them. Proxying keeps the console a single URL with nothing to set up.
 *
 * This is the only coupling between the demos, and it is one-directional and optional:
 * neither Python agent knows this exists, and if one is not deployed the endpoint returns
 * a message the console can show rather than failing.
 */
@Path("/agents")
@Produces(MediaType.APPLICATION_JSON)
public class AgentProxyResource {

    private static final Logger LOG = Logger.getLogger(AgentProxyResource.class);

    /** Runs take as long as an agent loop with tool calls, so this is generous. */
    private static final Duration TIMEOUT = Duration.ofSeconds(120);

    @ConfigProperty(name = "capybara.beaver.url", defaultValue = "http://beaver-sre:8000")
    String beaverUrl;

    @ConfigProperty(name = "capybara.otter.url", defaultValue = "http://otter-sre:8000")
    String otterUrl;

    @Inject
    ObjectMapper objectMapper;

    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

    /** Forwards the question and passes the answer straight back. */
    @POST
    @Path("/chat/{agent}")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response chat(@PathParam("agent") String agent, ChatRequest req) {
        String base = switch (agent) {
            case "beaver" -> beaverUrl;
            case "otter" -> otterUrl;
            default -> null;
        };
        if (base == null) {
            return Response.status(400).entity(Map.of("error", "unknown agent '" + agent + "'")).build();
        }
        try {
            String body = objectMapper.writeValueAsString(
                    Map.of("prompt", req == null || req.prompt() == null ? "" : req.prompt()));
            HttpRequest request = HttpRequest.newBuilder(URI.create(base + "/run"))
                    .header("Content-Type", MediaType.APPLICATION_JSON)
                    .timeout(TIMEOUT)
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            // Pass the body through untouched: the Python agent owns that shape, and
            // re-modelling it here would be a second place to keep in sync.
            return Response.status(response.statusCode())
                    .type(MediaType.APPLICATION_JSON)
                    .entity(response.body())
                    .build();
        } catch (Exception e) {
            LOG.warnf("%s unreachable at %s: %s", agent, base, e.getMessage());
            return Response.status(503).entity(Map.of(
                    "error", "The " + agent + " agent is not reachable. Deploy it: demos/agents/deploy.sh",
                    "detail", e.getClass().getSimpleName() + ": " + e.getMessage())).build();
        }
    }
}
