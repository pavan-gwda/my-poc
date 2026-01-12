package com.trading.config;

import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.errors.LogAndContinueExceptionHandler;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafkaStreams;
import org.springframework.kafka.annotation.KafkaStreamsDefaultConfiguration;
import org.springframework.kafka.config.KafkaStreamsConfiguration;

import java.util.HashMap;
import java.util.Map;

@Configuration
@EnableKafkaStreams
public class KafkaStreamsConfig {

    private final TradingProperties properties;

    public KafkaStreamsConfig(TradingProperties properties) {
        this.properties = properties;
    }

    @Bean(name = KafkaStreamsDefaultConfiguration.DEFAULT_STREAMS_CONFIG_BEAN_NAME)
    public KafkaStreamsConfiguration kafkaStreamsConfiguration() {
        Map<String, Object> props = new HashMap<>();

        // Basic Configuration
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "trading-streams-app");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, properties.kafka().bootstrapServers());

        // Serialization
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.StringSerde.class);
        props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.StringSerde.class);

        // Processing Guarantees
        // Use AT_LEAST_ONCE for local dev (EXACTLY_ONCE_V2 requires proper broker config)
        // In production, use EXACTLY_ONCE_V2 for financial data
        props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, StreamsConfig.AT_LEAST_ONCE);

        // Performance Tuning
        props.put(StreamsConfig.NUM_STREAM_THREADS_CONFIG, 3);
        props.put(StreamsConfig.COMMIT_INTERVAL_MS_CONFIG, 1000); // Commit every 1 second
        props.put(StreamsConfig.CACHE_MAX_BYTES_BUFFERING_CONFIG, 10 * 1024 * 1024); // 10MB cache

        // State Store Configuration
        props.put(StreamsConfig.STATE_DIR_CONFIG, "/tmp/kafka-streams");

        // Fault Tolerance - use 1 for local dev (single broker)
        props.put(StreamsConfig.REPLICATION_FACTOR_CONFIG, 1);
        props.put(StreamsConfig.DEFAULT_DESERIALIZATION_EXCEPTION_HANDLER_CLASS_CONFIG,
                LogAndContinueExceptionHandler.class);

        // Metrics
        props.put(StreamsConfig.METRICS_RECORDING_LEVEL_CONFIG, "INFO");

        // SSL Configuration (if enabled)
        addSslConfig(props);

        return new KafkaStreamsConfiguration(props);
    }

    private void addSslConfig(Map<String, Object> props) {
        var ssl = properties.kafka().ssl();
        if (ssl != null && ssl.enabled()) {
            props.put("security.protocol", "SSL");
            props.put("ssl.truststore.location", ssl.truststoreLocation());
            props.put("ssl.truststore.password", ssl.truststorePassword());

            if (ssl.keystoreLocation() != null) {
                props.put("ssl.keystore.location", ssl.keystoreLocation());
                props.put("ssl.keystore.password", ssl.keystorePassword());
            }
        }
    }
}
