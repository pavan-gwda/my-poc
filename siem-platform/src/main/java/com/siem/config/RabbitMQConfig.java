package com.siem.config;

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

@Configuration
public class RabbitMQConfig {

    private final SiemProperties properties;

    public RabbitMQConfig(SiemProperties properties) {
        this.properties = properties;
    }

    @Bean
    public ConnectionFactory connectionFactory() {
        CachingConnectionFactory factory = new CachingConnectionFactory();
        factory.setHost(properties.rabbitmq().host());
        factory.setPort(properties.rabbitmq().port());
        factory.setUsername(properties.rabbitmq().username());
        factory.setPassword(properties.rabbitmq().password());
        factory.setChannelCacheSize(25);
        return factory;
    }

    @Bean
    public RabbitAdmin rabbitAdmin(ConnectionFactory connectionFactory) {
        return new RabbitAdmin(connectionFactory);
    }

    @Bean
    public MessageConverter jsonMessageConverter() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        return new Jackson2JsonMessageConverter(mapper);
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter());
        return template;
    }

    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(jsonMessageConverter());
        factory.setConcurrentConsumers(3);
        factory.setMaxConcurrentConsumers(10);
        factory.setAcknowledgeMode(AcknowledgeMode.MANUAL);
        return factory;
    }

    // ==================== EXCHANGES ====================

    @Bean
    public TopicExchange alertExchange() {
        return ExchangeBuilder
                .topicExchange(properties.rabbitmq().exchanges().alerts())
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
    public Queue criticalAlertQueue() {
        return QueueBuilder
                .durable(properties.rabbitmq().queues().criticalAlerts())
                .withArgument("x-dead-letter-exchange", properties.rabbitmq().exchanges().deadLetter())
                .withArgument("x-dead-letter-routing-key", "dlq")
                .withArgument("x-message-ttl", 3600000)  // 1 hour TTL
                .build();
    }

    @Bean
    public Queue highAlertQueue() {
        return QueueBuilder
                .durable(properties.rabbitmq().queues().highAlerts())
                .withArgument("x-dead-letter-exchange", properties.rabbitmq().exchanges().deadLetter())
                .build();
    }

    @Bean
    public Queue mediumAlertQueue() {
        return QueueBuilder
                .durable(properties.rabbitmq().queues().mediumAlerts())
                .withArgument("x-dead-letter-exchange", properties.rabbitmq().exchanges().deadLetter())
                .build();
    }

    @Bean
    public Queue incidentCreationQueue() {
        return QueueBuilder
                .durable(properties.rabbitmq().queues().incidentCreation())
                .build();
    }

    @Bean
    public Queue deadLetterQueue() {
        return QueueBuilder
                .durable(properties.rabbitmq().queues().deadLetter())
                .build();
    }

    // ==================== BINDINGS ====================

    // Route alerts by severity using topic exchange
    // Routing key pattern: alert.{severity}.{type}

    @Bean
    public Binding criticalAlertBinding(Queue criticalAlertQueue, TopicExchange alertExchange) {
        return BindingBuilder.bind(criticalAlertQueue).to(alertExchange).with("alert.critical.*");
    }

    @Bean
    public Binding highAlertBinding(Queue highAlertQueue, TopicExchange alertExchange) {
        return BindingBuilder.bind(highAlertQueue).to(alertExchange).with("alert.high.*");
    }

    @Bean
    public Binding mediumAlertBinding(Queue mediumAlertQueue, TopicExchange alertExchange) {
        return BindingBuilder.bind(mediumAlertQueue).to(alertExchange).with("alert.medium.*");
    }

    // Critical alerts also go to incident creation
    @Bean
    public Binding incidentCreationBinding(Queue incidentCreationQueue, TopicExchange alertExchange) {
        return BindingBuilder.bind(incidentCreationQueue).to(alertExchange).with("alert.critical.*");
    }

    @Bean
    public Binding deadLetterBinding(Queue deadLetterQueue, DirectExchange deadLetterExchange) {
        return BindingBuilder.bind(deadLetterQueue).to(deadLetterExchange).with("dlq");
    }
}
