package com.capybara.sre;

import dev.langchain4j.agent.tool.ToolExecutionRequest;
import dev.langchain4j.service.Result;
import dev.langchain4j.service.tool.ToolExecution;
import io.quarkus.test.InjectMock;
import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.List;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.notNullValue;

@QuarkusTest
class InvestigationResourceTest {

    @InjectMock
    CapybaraSreAgent agent;

    @BeforeEach
    void setUp() {
        // Build ToolExecutionRequest (no mandatory fields beyond builder defaults)
        ToolExecutionRequest toolRequest = ToolExecutionRequest.builder()
                .id("tool-1")
                .name("list_records")
                .arguments("{\"plan\":\"free\"}")
                .build();

        // ToolExecution requires InvocationContext in 1.16.2 — mock it to keep the test hermetic
        ToolExecution toolExecution = Mockito.mock(ToolExecution.class);
        Mockito.when(toolExecution.request()).thenReturn(toolRequest);
        Mockito.when(toolExecution.result()).thenReturn("42 records found");

        Result<String> cannedResult = Result.<String>builder()
                .content("All systems nominal. Found 42 capybara records. No action needed.")
                .toolExecutions(List.of(toolExecution))
                .build();

        Mockito.when(agent.investigate(Mockito.anyString())).thenReturn(cannedResult);
    }

    @Test
    void chatReturnsContractShape() {
        given().contentType("application/json")
                .body("{\"prompt\":\"list the capybara records\"}")
        .when().post("/chat")
        .then().statusCode(200)
                .body("response", notNullValue())
                .body("runId", notNullValue())
                .body("toolCalls", notNullValue())
                .body("toolCalls", hasSize(1))
                .body("toolCalls[0].name", is("list_records"))
                .body("toolCalls[0].result", is("42 records found"))
                .body("toolCalls[0].args.plan", org.hamcrest.Matchers.equalTo("free"))
                // the UI needs to know which tool path produced this run
                .body("toolPath", is("mcp"))
                // the judge is mocked out here, so evaluations is present but empty
                .body("evaluations", notNullValue());
    }
}
