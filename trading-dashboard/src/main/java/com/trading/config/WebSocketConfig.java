package com.trading.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * WebSocket configuration for real-time updates to the trading dashboard.
 *
 * Architecture:
 * - STOMP protocol over WebSocket
 * - Simple broker for pub/sub
 * - User destinations for targeted notifications
 *
 * Endpoints:
 * - /ws - WebSocket handshake endpoint
 * - /topic/* - Broadcast topics (prices, announcements)
 * - /user/*///notifications - User-specific notifications

@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        // Enable simple in-memory broker for topics and queues
        registry.enableSimpleBroker(
                "/topic",   // Broadcast destinations
                "/queue"    // Point-to-point destinations
        );

        // Prefix for messages FROM clients TO server
        registry.setApplicationDestinationPrefixes("/app");

        // Prefix for user-specific destinations
        registry.setUserDestinationPrefix("/user");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // Primary WebSocket endpoint
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*") // Configure properly in production!
                .withSockJS(); // Fallback for browsers without WebSocket support
    }
}
