package com.siem.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

@Validated
@ConfigurationProperties(prefix = "siem")
public record SiemProperties(
    @NotNull KafkaProperties kafka,
    @NotNull RabbitMQProperties rabbitmq,
    @NotNull DetectionProperties detection,
    SimulatorProperties simulator
) {
    public record KafkaProperties(
        @NotBlank String bootstrapServers,
        @NotNull TopicProperties topics
    ) {}

    public record TopicProperties(
        // Raw log topics
        String rawAuthLogs,
        String rawFirewallLogs,
        String rawWebLogs,
        String rawDnsLogs,
        String rawEndpointLogs,
        // Processed topics
        String normalizedLogs,
        String alerts,
        String threats,
        String metrics
    ) {}

    public record RabbitMQProperties(
        @NotBlank String host,
        int port,
        @NotBlank String username,
        @NotBlank String password,
        @NotNull QueueProperties queues,
        @NotNull ExchangeProperties exchanges
    ) {
        public RabbitMQProperties {
            if (port == 0) port = 5672;
        }
    }

    public record QueueProperties(
        String criticalAlerts,
        String highAlerts,
        String mediumAlerts,
        String incidentCreation,
        String deadLetter
    ) {}

    public record ExchangeProperties(
        String alerts,
        String deadLetter
    ) {}

    public record DetectionProperties(
        @NotNull BruteForceConfig bruteForce,
        @NotNull PortScanConfig portScan,
        @NotNull ExfiltrationConfig exfiltration
    ) {}

    public record BruteForceConfig(
        @Positive int windowMinutes,
        @Positive int threshold
    ) {}

    public record PortScanConfig(
        @Positive int windowMinutes,
        @Positive int threshold
    ) {}

    public record ExfiltrationConfig(
        @Positive int windowMinutes,
        @Positive long bytesThreshold
    ) {}

    public record SimulatorProperties(
        boolean enabled
    ) {
        public SimulatorProperties {
            // Default to enabled if not specified
        }
    }
}
