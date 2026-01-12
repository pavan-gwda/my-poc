package com.trading.queue;

import com.trading.model.Notification;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

/**
 * Consumer for dead letter queue (DLQ).
 *
 * Messages end up here when:
 * 1. Max retries exceeded
 * 2. Message rejected without requeue
 * 3. Message TTL expired
 *
 * DLQ handling strategies:
 * - Log for manual review
 * - Alert operations team
 * - Store in database for later analysis
 * - Attempt alternative delivery method
 */
@Component
public class DeadLetterQueueConsumer {

    private static final Logger log = LoggerFactory.getLogger(DeadLetterQueueConsumer.class);

    @RabbitListener(queues = "${trading.rabbitmq.queues.dead-letter}")
    public void handleDeadLetter(Notification notification) {
        log.error("DEAD LETTER: Notification failed permanently - ID: {}, Type: {}, User: {}, Retries: {}",
                notification.notificationId(),
                notification.type(),
                notification.userId(),
                notification.retryCount());

        // In production:
        // 1. Store in database for manual review
        // 2. Alert operations team
        // 3. Update notification status to FAILED
        // 4. Consider alternative delivery methods

        handleFailedNotification(notification);
    }

    private void handleFailedNotification(Notification notification) {
        // Strategy based on notification type
        switch (notification.type()) {
            case ORDER_FILLED, ORDER_REJECTED:
                // Critical: Alert operations team immediately
                log.error("CRITICAL: Order notification failed for user {}. Manual intervention required.",
                        notification.userId());
                // In production: Page on-call, create incident ticket
                break;

            case PRICE_ALERT:
                // Medium priority: Log and potentially notify user via alternative channel
                log.warn("Price alert delivery failed for user {}. Alert may be stale.",
                        notification.userId());
                break;

            case PORTFOLIO_UPDATE:
                // Low priority: Just log, user will see update on next refresh
                log.info("Portfolio update notification failed. Non-critical.");
                break;

            default:
                log.warn("Unhandled dead letter notification type: {}", notification.type());
        }
    }
}
