package com.trading.config;

import com.trading.model.PriceTick;
import com.trading.model.OhlcCandle;
import com.trading.model.Order;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.config.SslConfigs;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.*;
import org.springframework.kafka.listener.ContainerProperties;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.kafka.support.serializer.JsonDeserializer;
import org.springframework.kafka.support.serializer.JsonSerializer;
import org.springframework.util.backoff.FixedBackOff;

import java.util.HashMap;
import java.util.Map;

@Configuration
@EnableKafka
public class KafkaConfig {

    private final TradingProperties properties;

    public KafkaConfig(TradingProperties properties) {
        this.properties = properties;
    }

    // ==================== PRODUCER CONFIGURATION ====================

    @Bean
    public ProducerFactory<String, Object> producerFactory() {
        Map<String, Object> configProps = new HashMap<>();

        // Basic Configuration
        configProps.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, properties.kafka().bootstrapServers());
        configProps.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        configProps.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);

        // Production-grade reliability settings
        configProps.put(ProducerConfig.ACKS_CONFIG, "all"); // Wait for all replicas
        configProps.put(ProducerConfig.RETRIES_CONFIG, 3);
        configProps.put(ProducerConfig.RETRY_BACKOFF_MS_CONFIG, 1000);
        configProps.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true); // Exactly-once semantics

        // Performance tuning
        configProps.put(ProducerConfig.BATCH_SIZE_CONFIG, 16384); // 16KB batch
        configProps.put(ProducerConfig.LINGER_MS_CONFIG, 5); // Wait up to 5ms to batch
        configProps.put(ProducerConfig.BUFFER_MEMORY_CONFIG, 33554432); // 32MB buffer
        configProps.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "snappy");

        // SSL Configuration (if enabled)
        addSslConfig(configProps);

        return new DefaultKafkaProducerFactory<>(configProps);
    }

    @Bean
    public KafkaTemplate<String, Object> kafkaTemplate() {
        return new KafkaTemplate<>(producerFactory());
    }

    // ==================== CONSUMER CONFIGURATION ====================

    @Bean
    public ConsumerFactory<String, PriceTick> priceTickConsumerFactory() {
        return createConsumerFactory(PriceTick.class, "price-tick-consumer");
    }

    @Bean
    public ConsumerFactory<String, Order> orderConsumerFactory() {
        return createConsumerFactory(Order.class, "order-consumer");
    }

    private <T> ConsumerFactory<String, T> createConsumerFactory(Class<T> targetType, String groupId) {
        Map<String, Object> configProps = new HashMap<>();

        // Basic Configuration
        configProps.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, properties.kafka().bootstrapServers());
        configProps.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        configProps.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        configProps.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, JsonDeserializer.class);

        // Consumer behavior
        configProps.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        configProps.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false); // Manual commit for reliability
        configProps.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 500);
        configProps.put(ConsumerConfig.MAX_POLL_INTERVAL_MS_CONFIG, 300000); // 5 minutes

        // JSON Deserializer settings
        configProps.put(JsonDeserializer.TRUSTED_PACKAGES, "com.trading.model");
        configProps.put(JsonDeserializer.VALUE_DEFAULT_TYPE, targetType.getName());
        configProps.put(JsonDeserializer.USE_TYPE_INFO_HEADERS, false);

        // SSL Configuration
        addSslConfig(configProps);

        return new DefaultKafkaConsumerFactory<>(configProps);
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, PriceTick> priceTickListenerFactory() {
        return createListenerFactory(priceTickConsumerFactory());
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, Order> orderListenerFactory() {
        return createListenerFactory(orderConsumerFactory());
    }

    @Bean
    public ConsumerFactory<String, OhlcCandle> ohlcCandleConsumerFactory() {
        return createConsumerFactory(OhlcCandle.class, "ohlc-candle-consumer");
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, OhlcCandle> ohlcCandleListenerFactory() {
        return createListenerFactory(ohlcCandleConsumerFactory());
    }

    private <T> ConcurrentKafkaListenerContainerFactory<String, T> createListenerFactory(
            ConsumerFactory<String, T> consumerFactory) {
        ConcurrentKafkaListenerContainerFactory<String, T> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);

        // Production settings
        factory.setConcurrency(3); // 3 consumer threads
        factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.MANUAL_IMMEDIATE);

        // Error handling with retry
        factory.setCommonErrorHandler(new DefaultErrorHandler(
                new FixedBackOff(1000L, 3L) // Retry 3 times with 1 second delay
        ));

        return factory;
    }

    // ==================== SSL CONFIGURATION ====================

    private void addSslConfig(Map<String, Object> configProps) {
        var ssl = properties.kafka().ssl();
        if (ssl != null && ssl.enabled()) {
            configProps.put("security.protocol", "SSL");
            configProps.put(SslConfigs.SSL_TRUSTSTORE_LOCATION_CONFIG, ssl.truststoreLocation());
            configProps.put(SslConfigs.SSL_TRUSTSTORE_PASSWORD_CONFIG, ssl.truststorePassword());

            if (ssl.keystoreLocation() != null) {
                configProps.put(SslConfigs.SSL_KEYSTORE_LOCATION_CONFIG, ssl.keystoreLocation());
                configProps.put(SslConfigs.SSL_KEYSTORE_PASSWORD_CONFIG, ssl.keystorePassword());
            }
        }
    }

    // ==================== TOPIC CONFIGURATION ====================

    @Bean
    public KafkaAdmin kafkaAdmin() {
        Map<String, Object> configs = new HashMap<>();
        configs.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, properties.kafka().bootstrapServers());
        addSslConfig(configs);
        return new KafkaAdmin(configs);
    }

    // Note: replicas(1) for local dev (single broker). Use 3 in production.
    private static final int REPLICATION_FACTOR = 1;

    @Bean
    public NewTopic priceTicksTopic() {
        return TopicBuilder.name(properties.kafka().topics().priceTicks())
                .partitions(6)      // Partition by stock symbol for ordering
                .replicas(REPLICATION_FACTOR)
                .config("retention.ms", "86400000")      // 24 hour retention
                .config("cleanup.policy", "delete")
                .build();
    }

    @Bean
    public NewTopic ohlcCandlesTopic() {
        return TopicBuilder.name(properties.kafka().topics().ohlcCandles())
                .partitions(6)
                .replicas(REPLICATION_FACTOR)
                .config("retention.ms", "604800000")     // 7 day retention
                .config("cleanup.policy", "delete")
                .build();
    }

    @Bean
    public NewTopic ordersTopic() {
        return TopicBuilder.name(properties.kafka().topics().orders())
                .partitions(6)
                .replicas(REPLICATION_FACTOR)
                .config("retention.ms", "604800000")
                .build();
    }

    @Bean
    public NewTopic portfolioUpdatesTopic() {
        return TopicBuilder.name(properties.kafka().topics().portfolioUpdates())
                .partitions(3)
                .replicas(REPLICATION_FACTOR)
                .config("retention.ms", "259200000")     // 3 day retention
                .config("cleanup.policy", "compact")     // Keep latest per key
                .build();
    }

    @Bean
    public NewTopic alertsTopic() {
        return TopicBuilder.name(properties.kafka().topics().alerts())
                .partitions(3)
                .replicas(REPLICATION_FACTOR)
                .build();
    }

    @Bean
    public NewTopic holdingsBySymbolTopic() {
        return TopicBuilder.name(properties.kafka().topics().holdingsBySymbol())
                .partitions(6)
                .replicas(REPLICATION_FACTOR)
                .config("cleanup.policy", "compact")  // Keep latest holdings per symbol
                .build();
    }
}
