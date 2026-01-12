package com.ai.agent.controller;

import com.ai.agent.service.AgentService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * REST API for interacting with the AI Agent.
 */
@RestController
@RequestMapping("/api/agent")
@CrossOrigin(origins = "*")
public class AgentController {

    private final AgentService agentService;

    public AgentController(AgentService agentService) {
        this.agentService = agentService;
    }

    /**
     * Chat with the agent.
     *
     * Example requests:
     * - "What is 25 * 47?"
     * - "What's the weather in Tokyo?"
     * - "Show me all electronics products under $200"
     * - "Calculate the total value of laptop stock"
     */
    @PostMapping("/chat")
    public ResponseEntity<ChatResponse> chat(@RequestBody ChatRequest request) {
        String response = agentService.chat(request.message());
        return ResponseEntity.ok(new ChatResponse(response));
    }

    /**
     * Simple GET endpoint for quick testing.
     */
    @GetMapping("/chat")
    public ResponseEntity<ChatResponse> chatGet(@RequestParam String message) {
        String response = agentService.chat(message);
        return ResponseEntity.ok(new ChatResponse(response));
    }

    /**
     * Health check
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "agent", "ready"
        ));
    }

    // DTOs
    public record ChatRequest(String message) {}
    public record ChatResponse(String response) {}
}
