package com.ai.agent.service;

import com.ai.agent.tools.CalculatorTool;
import com.ai.agent.tools.DatabaseTool;
import com.ai.agent.tools.WeatherTool;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * AI Agent Service using LangChain4j.
 *
 * KEY CONCEPTS:
 *
 * 1. TOOLS: Functions the LLM can call (Calculator, Weather, Database)
 *
 * 2. ReAct PATTERN: Reasoning + Acting
 *    - LLM reasons about what to do
 *    - Calls a tool if needed
 *    - Observes the result
 *    - Continues until task is complete
 *
 * 3. MEMORY: Conversation history for context
 *
 * 4. AiServices: LangChain4j's way to create a proxy that:
 *    - Sends messages to LLM
 *    - Parses tool calls from LLM response
 *    - Executes tools
 *    - Sends results back to LLM
 */
@Service
public class AgentService {

    private static final Logger log = LoggerFactory.getLogger(AgentService.class);

    private final ChatLanguageModel chatModel;
    private final CalculatorTool calculatorTool;
    private final WeatherTool weatherTool;
    private final DatabaseTool databaseTool;

    private Agent agent;

    public AgentService(
            ChatLanguageModel chatModel,
            CalculatorTool calculatorTool,
            WeatherTool weatherTool,
            DatabaseTool databaseTool) {
        this.chatModel = chatModel;
        this.calculatorTool = calculatorTool;
        this.weatherTool = weatherTool;
        this.databaseTool = databaseTool;
    }

    /**
     * Agent interface - LangChain4j creates implementation via proxy.
     *
     * The @SystemMessage defines the agent's personality and capabilities.
     */
    interface Agent {

        @SystemMessage("""
            You are an AI assistant that MUST use tools to answer questions.

            IMPORTANT: When you need information, you MUST call the tool - do not just describe what you would do.

            Available tools:
            - Calculator: add, subtract, multiply, divide, squareRoot, power
            - Weather: getCurrentWeather, getWeatherForecast
            - Database: getAllProducts, searchProductByName, getProductsByCategory, getProductsByPriceRange, checkStock, getTotalInventoryValue, getRecentOrders

            Rules:
            1. ALWAYS execute tools when needed - never just describe tool calls
            2. Wait for tool results before responding
            3. Use the actual tool output in your final answer
            """)
        String chat(@UserMessage String userMessage);
    }

    @PostConstruct
    public void init() {
        log.info("Initializing AI Agent with tools...");

        // Build the agent with:
        // - Chat model (Ollama)
        // - Tools (Calculator, Weather, Database)
        // - Memory (last 20 messages)
        this.agent = AiServices.builder(Agent.class)
                .chatLanguageModel(chatModel)
                .tools(calculatorTool, weatherTool, databaseTool)
                .chatMemory(MessageWindowChatMemory.withMaxMessages(20))
                .build();

        log.info("AI Agent initialized successfully!");
    }

    /**
     * Send a message to the agent and get a response.
     *
     * The agent will:
     * 1. Analyze the message
     * 2. Decide which tools to use (if any)
     * 3. Execute tools
     * 4. Formulate response
     */
    public String chat(String userMessage) {
        log.info("User: {}", userMessage);

        try {
            String response = agent.chat(userMessage);
            log.info("Agent: {}", response);
            return response;

        } catch (Exception e) {
            log.error("Agent error: {}", e.getMessage(), e);
            return "I encountered an error: " + e.getMessage();
        }
    }
}
