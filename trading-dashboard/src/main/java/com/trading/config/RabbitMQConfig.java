package com.trading.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.CachingConnectionFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.backoff.ExponentialBackOffPolicy;
import org.springframework.retry.policy.SimpleRetryPolicy;
import org.springframework.retry.support.RetryTemplate;

import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;

@Configuration
public class RabbitMQConfig {

    private final TradingProperties properties;

    public RabbitMQConfig(TradingProperties properties) {
        this.properties = properties;
    }

    // ==================== CONNECTION CONFIGURATION ====================

    @Bean
    public ConnectionFactory connectionFactory() throws NoSuchAlgorithmException, KeyManagementException {
        CachingConnectionFactory factory = new CachingConnectionFactory();
        factory.setHost(properties.rabbitmq().host());
        factory.setPort(properties.rabbitmq().port());
        factory.setUsername(properties.rabbitmq().username());
        factory.setPassword(properties.rabbitmq().password());

        // Channel cache size (default cache mode is CHANNEL)
        factory.setChannelCacheSize(25);

        // SSL Configuration
        var ssl = properties.rabbitmq().ssl();
        if (ssl != null && ssl.enabled()) {
            factory.getRabbitConnectionFactory().useSslProtocol();
        }

        return factory;
    }

    @Bean
    public RabbitAdmin rabbitAdmin(ConnectionFactory connectionFactory) {
        return new RabbitAdmin(connectionFactory);
    }

    // ==================== MESSAGE CONVERTER ====================

    @Bean
    public MessageConverter jsonMessageConverter() {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        return new Jackson2JsonMessageConverter(objectMapper);
    }

    // ==================== RABBIT TEMPLATE ====================

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter());

        // Enable publisher confirms for reliability
        template.setConfirmCallback((correlationData, ack, cause) -> {
            if (!ack) {
                // Log or handle failed delivery
                System.err.println("Message delivery failed: " + cause);
            }
        });

        // Enable returns for unroutable messages
        template.setReturnsCallback(returned -> {
            System.err.println("Message returned: " + returned.getMessage());
        });

        // Retry configuration
        template.setRetryTemplate(retryTemplate());

        return template;
    }

    @Bean
    public RetryTemplate retryTemplate() {
        RetryTemplate retryTemplate = new RetryTemplate();

        // Exponential backoff: 1s, 2s, 4s, 8s, 16s
        ExponentialBackOffPolicy backOffPolicy = new ExponentialBackOffPolicy();
        backOffPolicy.setInitialInterval(1000);
        backOffPolicy.setMultiplier(2.0);
        backOffPolicy.setMaxInterval(16000);
        retryTemplate.setBackOffPolicy(backOffPolicy);

        // Retry up to 5 times
        SimpleRetryPolicy retryPolicy = new SimpleRetryPolicy();
        retryPolicy.setMaxAttempts(5);
        retryTemplate.setRetryPolicy(retryPolicy);

        return retryTemplate;
    }

    // ==================== LISTENER CONTAINER FACTORY ====================

    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(jsonMessageConverter());

        // Concurrency settings
        factory.setConcurrentConsumers(3);
        factory.setMaxConcurrentConsumers(10);
        factory.setPrefetchCount(10);

        // Manual acknowledgment for reliability
        factory.setAcknowledgeMode(AcknowledgeMode.MANUAL);

        // Default requeue on failure (DLQ handles final failures)
        factory.setDefaultRequeueRejected(false);

        return factory;
    }

    // ==================== EXCHANGES ====================

    @Bean
    public DirectExchange notificationExchange() {
        return ExchangeBuilder
                .directExchange(properties.rabbitmq().exchanges().notifications())
                .durable(true)
                .build();
    }

    @Bean
    public DirectExchange deadLetterExchange() {
        return ExchangeBuilder
                .directExchange(properties.rabbitmq().exchanges().deadLetter())
                .durable(true)
                .build();
    }

    // ==================== QUEUES ====================

    @Bean
    public Queue notificationQueue() {
        return QueueBuilder
                .durable(properties.rabbitmq().queues().notifications())
                .withArgument("x-dead-letter-exchange", properties.rabbitmq().exchanges().deadLetter())
                .withArgument("x-dead-letter-routing-key", "dlq")
                .withArgument("x-message-ttl", 86400000) // 24 hour TTL
                .build();
    }

    @Bean
    public Queue emailQueue() {
        return QueueBuilder
                .durable(properties.rabbitmq().queues().email())
                .withArgument("x-dead-letter-exchange", properties.rabbitmq().exchanges().deadLetter())
                .withArgument("x-dead-letter-routing-key", "dlq")
                .build();
    }

    @Bean
    public Queue deadLetterQueue() {
        return QueueBuilder
                .durable(properties.rabbitmq().queues().deadLetter())
                .build();
    }

    // ==================== BINDINGS ====================

    @Bean
    public Binding notificationBinding(Queue notificationQueue, DirectExchange notificationExchange) {
        return BindingBuilder
                .bind(notificationQueue)
                .to(notificationExchange)
                .with("notification");
    }

    @Bean
    public Binding emailBinding(Queue emailQueue, DirectExchange notificationExchange) {
        return BindingBuilder
                .bind(emailQueue)
                .to(notificationExchange)
                .with("email");
    }

    @Bean
    public Binding deadLetterBinding(Queue deadLetterQueue, DirectExchange deadLetterExchange) {
        return BindingBuilder
                .bind(deadLetterQueue)
                .to(deadLetterExchange)
                .with("dlq");
    }
}
