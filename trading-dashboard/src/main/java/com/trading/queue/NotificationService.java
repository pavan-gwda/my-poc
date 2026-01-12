package com.trading.queue;

import com.trading.config.TradingProperties;
import com.trading.model.Notification;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

/**
 * Service for sending notifications through various channels.
 *
 * Channels:
 * - WebSocket: Real-time dashboard updates
 * - Email: Async via RabbitMQ email queue
 * - Push: Mobile push notifications
 * - SMS: Text messages (premium feature)
 */
@Service
public class NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationService.class);

    private final SimpMessagingTemplate webSocketTemplate;
    private final RabbitTemplate rabbitTemplate;
    private final TradingProperties properties;

    public NotificationService(
            SimpMessagingTemplate webSocketTemplate,
            RabbitTemplate rabbitTemplate,
            TradingProperties properties) {
        this.webSocketTemplate = webSocketTemplate;
        this.rabbitTemplate = rabbitTemplate;
        this.properties = properties;
    }

    /**
     * Send notification via WebSocket to specific user
     */
    public boolean sendWebSocket(Notification notification) {
        try {
            // Send to user-specific destination
            String destination = "/user/" + notification.userId() + "/notifications";
            webSocketTemplate.convertAndSend(destination, notification);

            log.debug("WebSocket notification sent to user {}: {}",
                    notification.userId(), notification.type());
            return true;

        } catch (Exception e) {
            log.error("Failed to send WebSocket notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * Broadcast notification to all connected users
     */
    public boolean broadcastWebSocket(Notification notification) {
        try {
            webSocketTemplate.convertAndSend("/topic/announcements", notification);
            log.debug("Broadcast notification sent: {}", notification.type());
            return true;

        } catch (Exception e) {
            log.error("Failed to broadcast notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * Queue email for async delivery
     */
    public void queueEmail(Notification notification) {
        try {
            // Increment retry count for tracking
            Notification emailNotification = notification.incrementRetry();

            rabbitTemplate.convertAndSend(
                    properties.rabbitmq().exchanges().notifications(),
                    "email",
                    emailNotification
            );

            log.debug("Email queued for notification: {}", notification.notificationId());

        } catch (Exception e) {
            log.error("Failed to queue email: {}", e.getMessage());
        }
    }

    /**
     * Send email (called from email queue consumer)
     */
    public boolean sendEmail(Notification notification) {
        try {
            // In production, integrate with email service (SendGrid, SES, etc.)
            // For demo, just log
            log.info("SENDING EMAIL to user {}: Subject='{}', Body='{}'",
                    notification.userId(),
                    notification.title(),
                    notification.message());

            // Simulate email sending delay
            Thread.sleep(100);

            return true;

        } catch (Exception e) {
            log.error("Failed to send email: {}", e.getMessage());
            return false;
        }
    }

    /**
     * Send push notification
     */
    public boolean sendPush(Notification notification) {
        try {
            // In production, integrate with FCM/APNS
            log.info("SENDING PUSH to user {}: '{}'",
                    notification.userId(),
                    notification.message());

            return true;

        } catch (Exception e) {
            log.error("Failed to send push notification: {}", e.getMessage());
            return false;
        }
    }

    /**
     * Send SMS notification (premium feature)
     */
    public boolean sendSms(Notification notification) {
        try {
            // In production, integrate with Twilio/Vonage
            log.info("SENDING SMS to user {}: '{}'",
                    notification.userId(),
                    notification.message());

            return true;

        } catch (Exception e) {
            log.error("Failed to send SMS: {}", e.getMessage());
            return false;
        }
    }
}
