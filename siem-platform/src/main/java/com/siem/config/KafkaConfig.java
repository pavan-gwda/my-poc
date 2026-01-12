package com.siem.config;

import com.siem.model.AuthEvent;
import com.siem.model.FirewallEvent;
import com.siem.model.DnsEvent;
import com.siem.model.SecurityAlert;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.producer.ProducerConfig;
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

    private final SiemProperties properties;

    public KafkaConfig(SiemProperties properties) {
        this.properties = properties;
    }

    // ==================== PRODUCERS ====================

    private Map<String, Object> producerProps() {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, properties.kafka().bootstrapServers());
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        return props;
    }

    @Bean
    public ProducerFactory<String, Object> producerFactory() {
        return new DefaultKafkaProducerFactory<>(producerProps());
    }

    @Bean
    public KafkaTemplate<String, Object> kafkaTemplate() {
        return new KafkaTemplate<>(producerFactory());
    }

    @Bean
    public ProducerFactory<String, AuthEvent> authProducerFactory() {
        return new DefaultKafkaProducerFactory<>(producerProps());
    }

    @Bean
    public KafkaTemplate<String, AuthEvent> authKafkaTemplate() {
        return new KafkaTemplate<>(authProducerFactory());
    }

    @Bean
    public ProducerFactory<String, FirewallEvent> firewallProducerFactory() {
        return new DefaultKafkaProducerFactory<>(producerProps());
    }

    @Bean
    public KafkaTemplate<String, FirewallEvent> firewallKafkaTemplate() {
        return new KafkaTemplate<>(firewallProducerFactory());
    }

    @Bean
    public ProducerFactory<String, DnsEvent> dnsProducerFactory() {
        return new DefaultKafkaProducerFactory<>(producerProps());
    }

    @Bean
    public KafkaTemplate<String, DnsEvent> dnsKafkaTemplate() {
        return new KafkaTemplate<>(dnsProducerFactory());
    }

    // ==================== CONSUMERS ====================

    @Bean
    public ConsumerFactory<String, AuthEvent> authEventConsumerFactory() {
        return createConsumerFactory(AuthEvent.class, "siem-auth-consumer");
    }

    @Bean
    public ConsumerFactory<String, FirewallEvent> firewallEventConsumerFactory() {
        return createConsumerFactory(FirewallEvent.class, "siem-firewall-consumer");
    }

    @Bean
    public ConsumerFactory<String, DnsEvent> dnsEventConsumerFactory() {
        return createConsumerFactory(DnsEvent.class, "siem-dns-consumer");
    }

    @Bean
    public ConsumerFactory<String, SecurityAlert> alertConsumerFactory() {
        return createConsumerFactory(SecurityAlert.class, "siem-alert-consumer");
    }

    private <T> ConsumerFactory<String, T> createConsumerFactory(Class<T> type, String groupId) {
        Map<String, Object> props = new HashMap<>();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, properties.kafka().bootstrapServers());
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, JsonDeserializer.class);
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);
        props.put(JsonDeserializer.TRUSTED_PACKAGES, "com.siem.model");
        props.put(JsonDeserializer.VALUE_DEFAULT_TYPE, type.getName());
        props.put(JsonDeserializer.USE_TYPE_INFO_HEADERS, false);
        return new DefaultKafkaConsumerFactory<>(props);
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, AuthEvent> authEventListenerFactory() {
        return createListenerFactory(authEventConsumerFactory());
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, FirewallEvent> firewallEventListenerFactory() {
        return createListenerFactory(firewallEventConsumerFactory());
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, DnsEvent> dnsEventListenerFactory() {
        return createListenerFactory(dnsEventConsumerFactory());
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, SecurityAlert> alertListenerFactory() {
        return createListenerFactory(alertConsumerFactory());
    }

    private <T> ConcurrentKafkaListenerContainerFactory<String, T> createListenerFactory(
            ConsumerFactory<String, T> consumerFactory) {
        ConcurrentKafkaListenerContainerFactory<String, T> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);
        factory.setConcurrency(3);
        factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.MANUAL_IMMEDIATE);
        factory.setCommonErrorHandler(new DefaultErrorHandler(new FixedBackOff(1000L, 3L)));
        return factory;
    }

    // ==================== TOPICS ====================

    @Bean
    public KafkaAdmin kafkaAdmin() {
        Map<String, Object> configs = new HashMap<>();
        configs.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, properties.kafka().bootstrapServers());
        return new KafkaAdmin(configs);
    }

    @Bean
    public NewTopic rawAuthLogsTopic() {
        return TopicBuilder.name(properties.kafka().topics().rawAuthLogs())
                .partitions(6).replicas(1).build();
    }

    @Bean
    public NewTopic rawFirewallLogsTopic() {
        return TopicBuilder.name(properties.kafka().topics().rawFirewallLogs())
                .partitions(6).replicas(1).build();
    }

    @Bean
    public NewTopic rawDnsLogsTopic() {
        return TopicBuilder.name(properties.kafka().topics().rawDnsLogs())
                .partitions(6).replicas(1).build();
    }

    @Bean
    public NewTopic alertsTopic() {
        return TopicBuilder.name(properties.kafka().topics().alerts())
                .partitions(3).replicas(1).build();
    }

    @Bean
    public NewTopic threatsTopic() {
        return TopicBuilder.name(properties.kafka().topics().threats())
                .partitions(3).replicas(1).build();
    }
}
