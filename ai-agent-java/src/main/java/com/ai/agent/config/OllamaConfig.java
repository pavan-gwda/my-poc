package com.ai.agent.config;

import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.ollama.OllamaChatModel;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Configuration for Ollama LLM.
 *
 * Ollama runs locally - no API keys needed!
 * Install: https://ollama.ai
 * Pull model: ollama pull llama3.2
 */
@Configuration
public class OllamaConfig {

    @Value("${ollama.base-url}")
    private String baseUrl;

    @Value("${ollama.model}")
    private String model;

    @Value("${ollama.temperature}")
    private double temperature;

    @Bean
    public ChatLanguageModel chatLanguageModel() {
        return OllamaChatModel.builder()
                .baseUrl(baseUrl)
                .modelName(model)
                .temperature(temperature)
                .timeout(Duration.ofSeconds(120))
                .build();
    }
}
