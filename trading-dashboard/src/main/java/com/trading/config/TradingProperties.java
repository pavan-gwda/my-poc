package com.trading.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

@Validated
@ConfigurationProperties(prefix = "trading")
public record TradingProperties(
    @NotNull KafkaProperties kafka,
    @NotNull RabbitMQProperties rabbitmq
) {
    public record KafkaProperties(
        @NotBlank String bootstrapServers,
        String schemaRegistryUrl,
        SslProperties ssl,
        TopicProperties topics
    ) {
        public KafkaProperties {
            if (topics == null) {
                topics = new TopicProperties(
                    "stock-price-ticks",
                    "stock-ohlc-candles",
                    "trading-orders",
                    "portfolio-updates",
                    "price-alerts",
                    "holdings-by-symbol"
                );
            }
        }
    }

    public record RabbitMQProperties(
        @NotBlank String host,
        int port,
        @NotBlank String username,
        @NotBlank String password,
        SslProperties ssl,
        QueueProperties queues,
        ExchangeProperties exchanges
    ) {
        public RabbitMQProperties {
            if (port == 0) port = 5672;
            if (queues == null) {
                queues = new QueueProperties(
                    "notification-queue",
                    "email-notification-queue",
                    "notification-dlq"
                );
            }
            if (exchanges == null) {
                exchanges = new ExchangeProperties(
                    "notification-exchange",
                    "notification-dlx"
                );
            }
        }
    }

    public record SslProperties(
        boolean enabled,
        String truststoreLocation,
        String truststorePassword,
        String keystoreLocation,
        String keystorePassword
    ) {}

    public record TopicProperties(
        String priceTicks,
        String ohlcCandles,
        String orders,
        String portfolioUpdates,
        String alerts,
        String holdingsBySymbol
    ) {}

    public record QueueProperties(
        String notifications,
        String email,
        String deadLetter
    ) {}

    public record ExchangeProperties(
        String notifications,
        String deadLetter
    ) {}
}
