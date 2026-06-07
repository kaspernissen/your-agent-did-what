package com.example.store;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.web.bind.annotation.*;

/**
 * Minimal REST endpoint for the Arconia convention-switching demo.
 * Accepts a plain-text prompt and returns the model response.
 * Sending a request through here will produce a GenAI span whose attribute
 * names change based on arconia.observations.conventions.opentelemetry.ai.flavor.
 *
 * Endpoint: POST /api/chat?prompt=<your prompt>
 */
@RestController
@RequestMapping("/api/chat")
public class ChatRestController {

    private final ChatClient chatClient;

    public ChatRestController(ChatClient.Builder chatClientBuilder) {
        this.chatClient = chatClientBuilder.build();
    }

    @PostMapping
    public ChatResponse chat(@RequestParam String prompt) {
        String response = chatClient.prompt()
                .user(prompt)
                .call()
                .content();
        return new ChatResponse(response);
    }

    public record ChatResponse(String response) {}
}
