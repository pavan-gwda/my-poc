package com.trading.streams;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.config.TradingProperties;
import com.trading.model.Notification;
import com.trading.model.PriceAlert;
import com.trading.model.PriceTick;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.processor.api.Processor;
import org.apache.kafka.streams.processor.api.ProcessorContext;
import org.apache.kafka.streams.processor.api.Record;
import org.apache.kafka.streams.state.KeyValueStore;
import org.apache.kafka.streams.state.StoreBuilder;
import org.apache.kafka.streams.state.Stores;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.support.serializer.JsonSerde;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

/**
 * Alert Engine - bridges Kafka Streams with RabbitMQ.
 *
 * Responsibilities:
 * 1. Store user price alerts in Kafka state store
 * 2. Check each price tick against active alerts
 * 3. When alert triggers, send notification to RabbitMQ queue
 *
 * This demonstrates the pattern of connecting streaming to queuing systems.
 */
@Component
public class AlertEngine {

    private static final Logger log = LoggerFactory.getLogger(AlertEngine.class);

    private static final String ALERT_STORE = "price-alerts-store";
    private static final String LAST_PRICE_STORE = "last-price-store";

    private final TradingProperties properties;
    private final ObjectMapper objectMapper;
    private final RabbitTemplate rabbitTemplate;

    public AlertEngine(
            TradingProperties properties,
            ObjectMapper objectMapper,
            RabbitTemplate rabbitTemplate) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        this.rabbitTemplate = rabbitTemplate;
    }

    @Autowired
    public void buildPipeline(StreamsBuilder streamsBuilder) {
        // Create Serdes
        Serde<PriceTick> priceTickSerde = new JsonSerde<>(PriceTick.class, objectMapper);
        Serde<PriceAlert> alertSerde = new JsonSerde<>(PriceAlert.class, objectMapper);
        Serde<AlertList> alertListSerde = new JsonSerde<>(AlertList.class, objectMapper);

        // Create state store for alerts (keyed by symbol for efficient lookup)
        StoreBuilder<KeyValueStore<String, AlertList>> alertStoreBuilder =
                Stores.keyValueStoreBuilder(
                        Stores.persistentKeyValueStore(ALERT_STORE),
                        Serdes.String(),
                        alertListSerde
                );

        // Create state store for last known prices (to detect crossings)
        StoreBuilder<KeyValueStore<String, BigDecimal>> lastPriceStoreBuilder =
                Stores.keyValueStoreBuilder(
                        Stores.persistentKeyValueStore(LAST_PRICE_STORE),
                        Serdes.String(),
                        new BigDecimalSerde()
                );

        streamsBuilder.addStateStore(alertStoreBuilder);
        streamsBuilder.addStateStore(lastPriceStoreBuilder);

        // Process price ticks to check alerts
        KStream<String, PriceTick> priceTicks = streamsBuilder
                .stream(
                        properties.kafka().topics().priceTicks(),
                        Consumed.with(Serdes.String(), priceTickSerde)
                );

        // Process each tick through alert checker
        priceTicks.process(
                () -> new AlertProcessor(rabbitTemplate, properties),
                ALERT_STORE, LAST_PRICE_STORE
        );

        // Also consume alert registration events
        KStream<String, PriceAlert> alertRegistrations = streamsBuilder
                .stream(
                        properties.kafka().topics().alerts(),
                        Consumed.with(Serdes.String(), alertSerde)
                );

        // Store new alerts in state store
        alertRegistrations.process(
                () -> new AlertRegistrationProcessor(),
                ALERT_STORE
        );

        log.info("Alert engine pipeline built successfully");
    }

    /**
     * Processor that checks each price tick against stored alerts
     */
    private static class AlertProcessor implements Processor<String, PriceTick, Void, Void> {

        private final RabbitTemplate rabbitTemplate;
        private final TradingProperties properties;
        private ProcessorContext<Void, Void> context;
        private KeyValueStore<String, AlertList> alertStore;
        private KeyValueStore<String, BigDecimal> lastPriceStore;

        AlertProcessor(RabbitTemplate rabbitTemplate, TradingProperties properties) {
            this.rabbitTemplate = rabbitTemplate;
            this.properties = properties;
        }

        @Override
        public void init(ProcessorContext<Void, Void> context) {
            this.context = context;
            this.alertStore = context.getStateStore(ALERT_STORE);
            this.lastPriceStore = context.getStateStore(LAST_PRICE_STORE);
        }

        @Override
        public void process(Record<String, PriceTick> record) {
            String symbol = record.key();
            PriceTick tick = record.value();

            // Get last known price for this symbol
            BigDecimal lastPrice = lastPriceStore.get(symbol);
            if (lastPrice == null) {
                lastPrice = tick.price(); // First tick, use current as baseline
            }

            // Get alerts for this symbol
            AlertList alerts = alertStore.get(symbol);
            if (alerts != null && !alerts.alerts().isEmpty()) {
                List<PriceAlert> triggeredAlerts = new ArrayList<>();
                List<PriceAlert> remainingAlerts = new ArrayList<>();

                for (PriceAlert alert : alerts.alerts()) {
                    if (alert.status() == PriceAlert.AlertStatus.ACTIVE) {
                        if (alert.shouldTrigger(lastPrice, tick.price())) {
                            // Alert triggered!
                            triggeredAlerts.add(alert.trigger());
                            sendNotification(alert, tick);
                        } else {
                            remainingAlerts.add(alert);
                        }
                    }
                }

                // Update store with remaining active alerts
                if (!triggeredAlerts.isEmpty()) {
                    alertStore.put(symbol, new AlertList(remainingAlerts));
                    log.info("Triggered {} alerts for {} at price {}",
                            triggeredAlerts.size(), symbol, tick.price());
                }
            }

            // Update last price
            lastPriceStore.put(symbol, tick.price());
        }

        private void sendNotification(PriceAlert alert, PriceTick tick) {
            try {
                String conditionText = switch (alert.condition()) {
                    case CROSSES_ABOVE -> "crossed above";
                    case CROSSES_BELOW -> "crossed below";
                    case CROSSES -> "crossed";
                };

                Notification notification = Notification.priceAlert(
                        alert.userId(),
                        alert.symbol(),
                        conditionText,
                        tick.price().doubleValue()
                );

                // Send to RabbitMQ notification queue
                rabbitTemplate.convertAndSend(
                        properties.rabbitmq().exchanges().notifications(),
                        "notification",
                        notification
                );

                log.info("Sent notification to RabbitMQ for alert: {} {} {}",
                        alert.symbol(), conditionText, alert.targetPrice());

            } catch (Exception e) {
                log.error("Failed to send notification for alert {}: {}",
                        alert.alertId(), e.getMessage());
            }
        }

        @Override
        public void close() {
            // Cleanup if needed
        }
    }

    /**
     * Processor that stores new alert registrations
     */
    private static class AlertRegistrationProcessor implements Processor<String, PriceAlert, Void, Void> {

        private KeyValueStore<String, AlertList> alertStore;

        @Override
        public void init(ProcessorContext<Void, Void> context) {
            this.alertStore = context.getStateStore(ALERT_STORE);
        }

        @Override
        public void process(Record<String, PriceAlert> record) {
            PriceAlert alert = record.value();
            String symbol = alert.symbol();

            // Get existing alerts for this symbol
            AlertList existing = alertStore.get(symbol);
            List<PriceAlert> alerts = existing != null ?
                    new ArrayList<>(existing.alerts()) : new ArrayList<>();

            // Add new alert
            alerts.add(alert);
            alertStore.put(symbol, new AlertList(alerts));

            log.info("Registered new alert for {}: {} @ {}",
                    symbol, alert.condition(), alert.targetPrice());
        }

        @Override
        public void close() {
            // Cleanup if needed
        }
    }

    /**
     * Wrapper for storing list of alerts in state store
     */
    public record AlertList(List<PriceAlert> alerts) {
        public AlertList {
            if (alerts == null) {
                alerts = new ArrayList<>();
            }
        }
    }

    /**
     * Simple Serde for BigDecimal
     */
    private static class BigDecimalSerde implements Serde<BigDecimal> {
        @Override
        public org.apache.kafka.common.serialization.Serializer<BigDecimal> serializer() {
            return (topic, data) -> data != null ? data.toString().getBytes() : null;
        }

        @Override
        public org.apache.kafka.common.serialization.Deserializer<BigDecimal> deserializer() {
            return (topic, data) -> data != null ? new BigDecimal(new String(data)) : null;
        }
    }
}
