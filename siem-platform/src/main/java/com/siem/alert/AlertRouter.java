package com.siem.alert;

import com.siem.config.SiemProperties;
import com.siem.model.SecurityAlert;
import com.siem.model.SecurityEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

/**
 * Routes alerts from Kafka to RabbitMQ based on severity.
 *
 * This is the bridge between streaming (Kafka) and queuing (RabbitMQ).
 *
 * Routing:
 * - CRITICAL -> critical-alert-queue + incident-creation-queue
 * - HIGH -> high-alert-queue
 * - MEDIUM -> medium-alert-queue
 * - LOW/INFO -> logged only, not queued
 */
@Service
public class AlertRouter {

    private static final Logger log = LoggerFactory.getLogger(AlertRouter.class);

    private final RabbitTemplate rabbitTemplate;
    private final SiemProperties properties;

    public AlertRouter(RabbitTemplate rabbitTemplate, SiemProperties properties) {
        this.rabbitTemplate = rabbitTemplate;
        this.properties = properties;
    }

    @KafkaListener(
            topics = "${siem.kafka.topics.alerts}",
            groupId = "siem-alert-router",
            containerFactory = "alertListenerFactory"
    )
    public void routeAlert(SecurityAlert alert) {
        log.info("Routing alert: {} - {} [{}]",
                alert.alertId(), alert.title(), alert.severity());

        String routingKey = buildRoutingKey(alert);

        try {
            rabbitTemplate.convertAndSend(
                    properties.rabbitmq().exchanges().alerts(),
                    routingKey,
                    alert
            );

            log.debug("Alert routed to RabbitMQ: {} -> {}", alert.alertId(), routingKey);

            // Track metrics
            trackAlertMetrics(alert);

        } catch (Exception e) {
            log.error("Failed to route alert {}: {}", alert.alertId(), e.getMessage());
            // In production, implement retry logic or fallback
        }
    }

    /**
     * Build routing key based on severity and type.
     * Pattern: alert.{severity}.{type}
     */
    private String buildRoutingKey(SecurityAlert alert) {
        String severity = alert.severity().name().toLowerCase();
        String type = alert.type().name().toLowerCase();
        return String.format("alert.%s.%s", severity, type);
    }

    private void trackAlertMetrics(SecurityAlert alert) {
        // In production, emit metrics to Prometheus/StatsD
        switch (alert.severity()) {
            case CRITICAL -> log.warn("CRITICAL ALERT: {}", alert.title());
            case HIGH -> log.warn("HIGH ALERT: {}", alert.title());
            case MEDIUM -> log.info("MEDIUM ALERT: {}", alert.title());
            default -> log.debug("LOW/INFO ALERT: {}", alert.title());
        }
    }
}
