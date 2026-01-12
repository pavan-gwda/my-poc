package com.trading.service;

import com.trading.config.TradingProperties;
import com.trading.model.PriceAlert;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Service for price alert management.
 *
 * Alerts are:
 * 1. Stored in-memory (database in production)
 * 2. Published to Kafka for stream processing
 * 3. Stored in Kafka Streams state store for real-time checking
 */
@Service
public class AlertService {

    private static final Logger log = LoggerFactory.getLogger(AlertService.class);

    private final KafkaTemplate<String, Object> kafkaTemplate;
    private final TradingProperties properties;

    // In-memory alert storage (use database in production)
    private final Map<String, PriceAlert> alerts = new ConcurrentHashMap<>();

    public AlertService(KafkaTemplate<String, Object> kafkaTemplate, TradingProperties properties) {
        this.kafkaTemplate = kafkaTemplate;
        this.properties = properties;
    }

    public PriceAlert createAlert(String userId, String symbol,
                                  PriceAlert.AlertCondition condition, double targetPrice) {

        PriceAlert alert = PriceAlert.create(userId, symbol.toUpperCase(), condition, targetPrice);

        // Store locally
        alerts.put(alert.alertId(), alert);

        // Publish to Kafka for stream processing
        // Key by symbol so alert engine can efficiently look up alerts per symbol
        kafkaTemplate.send(
                properties.kafka().topics().alerts(),
                symbol.toUpperCase(),
                alert
        );

        log.info("Alert created: {} for {} {} @ {}",
                alert.alertId(), symbol, condition, targetPrice);

        return alert;
    }

    public List<PriceAlert> getAlertsByUser(String userId) {
        return alerts.values().stream()
                .filter(a -> a.userId().equals(userId))
                .filter(a -> a.status() == PriceAlert.AlertStatus.ACTIVE)
                .collect(Collectors.toList());
    }

    public List<PriceAlert> getAlertsBySymbol(String symbol) {
        return alerts.values().stream()
                .filter(a -> a.symbol().equals(symbol.toUpperCase()))
                .filter(a -> a.status() == PriceAlert.AlertStatus.ACTIVE)
                .collect(Collectors.toList());
    }

    public PriceAlert getAlert(String alertId) {
        return alerts.get(alertId);
    }

    public boolean cancelAlert(String alertId, String userId) {
        PriceAlert alert = alerts.get(alertId);
        if (alert == null || !alert.userId().equals(userId)) {
            return false;
        }

        if (alert.status() != PriceAlert.AlertStatus.ACTIVE) {
            log.warn("Cannot cancel alert {} in status {}", alertId, alert.status());
            return false;
        }

        // Update status
        PriceAlert cancelledAlert = new PriceAlert(
                alert.alertId(),
                alert.userId(),
                alert.symbol(),
                alert.condition(),
                alert.targetPrice(),
                PriceAlert.AlertStatus.CANCELLED,
                alert.createdAt(),
                null
        );
        alerts.put(alertId, cancelledAlert);

        log.info("Alert cancelled: {}", alertId);
        return true;
    }

    public void markTriggered(String alertId) {
        PriceAlert alert = alerts.get(alertId);
        if (alert != null) {
            alerts.put(alertId, alert.trigger());
            log.info("Alert triggered: {}", alertId);
        }
    }
}
