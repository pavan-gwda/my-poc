package com.siem.service;

import com.siem.model.SecurityAlert;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

/**
 * Listens for alerts on Kafka and persists them to the AlertService.
 */
@Component
public class AlertPersistenceListener {

    private static final Logger log = LoggerFactory.getLogger(AlertPersistenceListener.class);

    private final AlertService alertService;

    public AlertPersistenceListener(AlertService alertService) {
        this.alertService = alertService;
    }

    @KafkaListener(
            topics = "${siem.kafka.topics.alerts}",
            groupId = "siem-alert-persistence",
            containerFactory = "alertListenerFactory"
    )
    public void persistAlert(SecurityAlert alert, Acknowledgment ack) {
        try {
            alertService.storeAlert(alert);
            log.debug("Persisted alert: {} - {}", alert.alertId(), alert.title());
            ack.acknowledge();
        } catch (Exception e) {
            log.error("Failed to persist alert: {}", e.getMessage());
            // Don't ack - will be retried
        }
    }
}
