package com.siem.alert;

import com.rabbitmq.client.Channel;
import com.siem.model.SecurityAlert;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.support.AmqpHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.stereotype.Service;

import java.io.IOException;

/**
 * Handles alert notifications from RabbitMQ queues.
 *
 * Different handlers for different severity levels:
 * - Critical: PagerDuty, SMS, immediate escalation
 * - High: Slack/Teams, email to SOC
 * - Medium: Email digest, dashboard update
 */
@Service
public class AlertNotificationHandler {

    private static final Logger log = LoggerFactory.getLogger(AlertNotificationHandler.class);

    /**
     * Handle critical alerts - require immediate attention
     */
    @RabbitListener(
            queues = "${siem.rabbitmq.queues.critical-alerts}",
            containerFactory = "rabbitListenerContainerFactory"
    )
    public void handleCriticalAlert(
            SecurityAlert alert,
            Channel channel,
            @Header(AmqpHeaders.DELIVERY_TAG) long deliveryTag) throws IOException {

        log.error("🚨 CRITICAL ALERT: {} - {}", alert.title(), alert.description());

        try {
            // 1. Page on-call via PagerDuty
            sendPagerDutyAlert(alert);

            // 2. Send SMS to security team
            sendSmsAlert(alert);

            // 3. Post to war room Slack channel
            sendSlackAlert(alert, "#security-war-room");

            // 4. Create incident ticket
            createIncidentTicket(alert);

            channel.basicAck(deliveryTag, false);
            log.info("Critical alert processed: {}", alert.alertId());

        } catch (Exception e) {
            log.error("Failed to process critical alert: {}", e.getMessage());
            channel.basicNack(deliveryTag, false, true);
        }
    }

    /**
     * Handle high severity alerts
     */
    @RabbitListener(
            queues = "${siem.rabbitmq.queues.high-alerts}",
            containerFactory = "rabbitListenerContainerFactory"
    )
    public void handleHighAlert(
            SecurityAlert alert,
            Channel channel,
            @Header(AmqpHeaders.DELIVERY_TAG) long deliveryTag) throws IOException {

        log.warn("⚠️ HIGH ALERT: {} - {}", alert.title(), alert.description());

        try {
            // 1. Post to SOC Slack channel
            sendSlackAlert(alert, "#soc-alerts");

            // 2. Send email to security team
            sendEmailAlert(alert, "soc@company.com");

            channel.basicAck(deliveryTag, false);

        } catch (Exception e) {
            log.error("Failed to process high alert: {}", e.getMessage());
            channel.basicNack(deliveryTag, false, true);
        }
    }

    /**
     * Handle medium severity alerts
     */
    @RabbitListener(
            queues = "${siem.rabbitmq.queues.medium-alerts}",
            containerFactory = "rabbitListenerContainerFactory"
    )
    public void handleMediumAlert(
            SecurityAlert alert,
            Channel channel,
            @Header(AmqpHeaders.DELIVERY_TAG) long deliveryTag) throws IOException {

        log.info("📋 MEDIUM ALERT: {} - {}", alert.title(), alert.description());

        try {
            // Add to daily digest
            addToDigest(alert);

            // Update dashboard
            updateDashboard(alert);

            channel.basicAck(deliveryTag, false);

        } catch (Exception e) {
            log.error("Failed to process medium alert: {}", e.getMessage());
            channel.basicNack(deliveryTag, false, true);
        }
    }

    /**
     * Handle incident creation requests
     */
    @RabbitListener(
            queues = "${siem.rabbitmq.queues.incident-creation}",
            containerFactory = "rabbitListenerContainerFactory"
    )
    public void handleIncidentCreation(
            SecurityAlert alert,
            Channel channel,
            @Header(AmqpHeaders.DELIVERY_TAG) long deliveryTag) throws IOException {

        log.info("Creating incident for alert: {}", alert.alertId());

        try {
            String incidentId = createIncidentTicket(alert);
            log.info("Incident created: {} for alert {}", incidentId, alert.alertId());

            channel.basicAck(deliveryTag, false);

        } catch (Exception e) {
            log.error("Failed to create incident: {}", e.getMessage());
            channel.basicNack(deliveryTag, false, true);
        }
    }

    // ==================== NOTIFICATION IMPLEMENTATIONS ====================
    // In production, these would integrate with real services

    private void sendPagerDutyAlert(SecurityAlert alert) {
        log.info("[PAGERDUTY] Paging on-call for: {}", alert.title());
        // Integration with PagerDuty API
    }

    private void sendSmsAlert(SecurityAlert alert) {
        log.info("[SMS] Sending SMS for critical alert: {}", alert.alertId());
        // Integration with Twilio/Vonage
    }

    private void sendSlackAlert(SecurityAlert alert, String channel) {
        log.info("[SLACK] Posting to {}: {}", channel, alert.title());
        // Integration with Slack API
    }

    private void sendEmailAlert(SecurityAlert alert, String recipient) {
        log.info("[EMAIL] Sending to {}: {}", recipient, alert.title());
        // Integration with email service
    }

    private String createIncidentTicket(SecurityAlert alert) {
        String incidentId = "INC-" + System.currentTimeMillis();
        log.info("[JIRA/SNOW] Creating incident {}: {}", incidentId, alert.title());
        // Integration with Jira/ServiceNow
        return incidentId;
    }

    private void addToDigest(SecurityAlert alert) {
        log.debug("[DIGEST] Added to daily digest: {}", alert.alertId());
        // Store for daily summary email
    }

    private void updateDashboard(SecurityAlert alert) {
        log.debug("[DASHBOARD] Updated for: {}", alert.alertId());
        // Push to WebSocket for real-time dashboard
    }
}
