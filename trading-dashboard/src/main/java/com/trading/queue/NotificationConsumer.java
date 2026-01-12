package com.trading.queue;

import com.rabbitmq.client.Channel;
import com.trading.model.Notification;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.support.AmqpHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * RabbitMQ consumer for processing notifications asynchronously.
 *
 * Why use a queue for notifications?
 * 1. Decoupling - Alert engine doesn't wait for email to send
 * 2. Retry - Failed notifications can be retried (dead letter queue)
 * 3. Rate limiting - Can control notification throughput
 * 4. Multiple channels - Different queues for email, SMS, push
 *
 * Manual acknowledgment ensures at-least-once delivery.
 */
@Component
public class NotificationConsumer {

    private static final Logger log = LoggerFactory.getLogger(NotificationConsumer.class);
    private static final int MAX_RETRIES = 3;

    private final NotificationService notificationService;

    public NotificationConsumer(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    /**
     * Process notifications from the main notification queue.
     * Uses manual acknowledgment for reliability.
     */
    @RabbitListener(
            queues = "${trading.rabbitmq.queues.notifications}",
            containerFactory = "rabbitListenerContainerFactory"
    )
    public void processNotification(
            Notification notification,
            Channel channel,
            @Header(AmqpHeaders.DELIVERY_TAG) long deliveryTag) throws IOException {

        log.info("Processing notification: {} - {} for user {}",
                notification.notificationId(),
                notification.type(),
                notification.userId());

        try {
            // Route to appropriate handler based on notification type
            boolean success = switch (notification.type()) {
                case PRICE_ALERT -> handlePriceAlert(notification);
                case ORDER_FILLED -> handleOrderFilled(notification);
                case ORDER_CANCELLED, ORDER_REJECTED -> handleOrderUpdate(notification);
                case PORTFOLIO_UPDATE -> handlePortfolioUpdate(notification);
                case SYSTEM_ANNOUNCEMENT -> handleSystemAnnouncement(notification);
            };

            if (success) {
                // Acknowledge successful processing
                channel.basicAck(deliveryTag, false);
                log.info("Successfully processed notification: {}", notification.notificationId());
            } else {
                // Retry or reject based on retry count
                handleFailure(notification, channel, deliveryTag, null);
            }

        } catch (Exception e) {
            log.error("Error processing notification {}: {}",
                    notification.notificationId(), e.getMessage());
            handleFailure(notification, channel, deliveryTag, e);
        }
    }

    /**
     * Process email notifications from dedicated email queue.
     * Separate queue allows for different throughput/retry policies.
     */
    @RabbitListener(
            queues = "${trading.rabbitmq.queues.email}",
            containerFactory = "rabbitListenerContainerFactory"
    )
    public void processEmailNotification(
            Notification notification,
            Channel channel,
            @Header(AmqpHeaders.DELIVERY_TAG) long deliveryTag) throws IOException {

        log.info("Processing email notification: {}", notification.notificationId());

        try {
            boolean sent = notificationService.sendEmail(notification);

            if (sent) {
                channel.basicAck(deliveryTag, false);
                log.info("Email sent successfully for notification: {}", notification.notificationId());
            } else {
                // Requeue for retry
                channel.basicNack(deliveryTag, false, true);
            }

        } catch (Exception e) {
            log.error("Failed to send email for {}: {}", notification.notificationId(), e.getMessage());
            // Send to dead letter queue after max retries
            if (notification.retryCount() >= MAX_RETRIES) {
                channel.basicReject(deliveryTag, false); // Don't requeue, goes to DLQ
            } else {
                channel.basicNack(deliveryTag, false, true); // Requeue for retry
            }
        }
    }

    private boolean handlePriceAlert(Notification notification) {
        log.info("Price alert for user {}: {}", notification.userId(), notification.message());

        // Send via appropriate channels
        boolean success = true;

        // WebSocket for real-time dashboard update
        success &= notificationService.sendWebSocket(notification);

        // Also queue email for later delivery
        notificationService.queueEmail(notification);

        return success;
    }

    private boolean handleOrderFilled(Notification notification) {
        log.info("Order filled for user {}: {}", notification.userId(), notification.message());

        // High priority - send immediately via all channels
        notificationService.sendWebSocket(notification);
        notificationService.sendPush(notification);
        notificationService.queueEmail(notification);

        return true;
    }

    private boolean handleOrderUpdate(Notification notification) {
        log.info("Order update for user {}: {}", notification.userId(), notification.message());

        notificationService.sendWebSocket(notification);
        notificationService.queueEmail(notification);

        return true;
    }

    private boolean handlePortfolioUpdate(Notification notification) {
        // Portfolio updates are high volume, only send to WebSocket
        return notificationService.sendWebSocket(notification);
    }

    private boolean handleSystemAnnouncement(Notification notification) {
        log.info("System announcement: {}", notification.message());

        // Broadcast to all connected users
        notificationService.broadcastWebSocket(notification);
        return true;
    }

    private void handleFailure(
            Notification notification,
            Channel channel,
            long deliveryTag,
            Exception error) throws IOException {

        if (notification.retryCount() >= MAX_RETRIES) {
            // Max retries exceeded, reject to dead letter queue
            log.warn("Max retries exceeded for notification {}, sending to DLQ",
                    notification.notificationId());
            channel.basicReject(deliveryTag, false);
        } else {
            // Requeue for retry
            log.info("Requeuing notification {} for retry (attempt {})",
                    notification.notificationId(), notification.retryCount() + 1);
            channel.basicNack(deliveryTag, false, true);
        }
    }
}
