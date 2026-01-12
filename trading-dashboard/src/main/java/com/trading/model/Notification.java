package com.trading.model;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Notification message sent via RabbitMQ for async processing
 */
public record Notification(
    String notificationId,
    String userId,
    NotificationType type,
    NotificationChannel channel,
    String title,
    String message,
    Map<String, Object> metadata,
    NotificationStatus status,
    Instant createdAt,
    int retryCount
) {
    public enum NotificationType {
        PRICE_ALERT,
        ORDER_FILLED,
        ORDER_CANCELLED,
        ORDER_REJECTED,
        PORTFOLIO_UPDATE,
        SYSTEM_ANNOUNCEMENT
    }

    public enum NotificationChannel {
        EMAIL,
        SMS,
        PUSH,
        WEBSOCKET
    }

    public enum NotificationStatus {
        PENDING,
        SENT,
        FAILED,
        DELIVERED
    }

    public static Notification priceAlert(String userId, String symbol, String condition, double price) {
        return new Notification(
            UUID.randomUUID().toString(),
            userId,
            NotificationType.PRICE_ALERT,
            NotificationChannel.EMAIL,
            "Price Alert: " + symbol,
            String.format("%s has %s $%.2f", symbol, condition, price),
            Map.of("symbol", symbol, "price", price, "condition", condition),
            NotificationStatus.PENDING,
            Instant.now(),
            0
        );
    }

    public static Notification orderFilled(String userId, Order order) {
        return new Notification(
            UUID.randomUUID().toString(),
            userId,
            NotificationType.ORDER_FILLED,
            NotificationChannel.EMAIL,
            "Order Filled: " + order.symbol(),
            String.format("Your %s order for %s shares of %s has been filled at $%s",
                order.side(), order.filledQuantity(), order.symbol(), order.averagePrice()),
            Map.of("orderId", order.orderId(), "symbol", order.symbol()),
            NotificationStatus.PENDING,
            Instant.now(),
            0
        );
    }

    public Notification incrementRetry() {
        return new Notification(
            notificationId, userId, type, channel, title, message,
            metadata, status, createdAt, retryCount + 1
        );
    }

    public Notification withStatus(NotificationStatus newStatus) {
        return new Notification(
            notificationId, userId, type, channel, title, message,
            metadata, newStatus, createdAt, retryCount
        );
    }
}
