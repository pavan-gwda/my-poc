package com.trading.model;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record PriceAlert(
    String alertId,
    String userId,
    String symbol,
    AlertCondition condition,
    BigDecimal targetPrice,
    AlertStatus status,
    Instant createdAt,
    Instant triggeredAt
) {
    public enum AlertCondition {
        CROSSES_ABOVE,    // Alert when price goes above target
        CROSSES_BELOW,    // Alert when price goes below target
        CROSSES           // Alert when price crosses target in either direction
    }

    public enum AlertStatus {
        ACTIVE,
        TRIGGERED,
        CANCELLED,
        EXPIRED
    }

    public static PriceAlert create(String userId, String symbol, AlertCondition condition, double targetPrice) {
        return new PriceAlert(
            UUID.randomUUID().toString(),
            userId,
            symbol,
            condition,
            BigDecimal.valueOf(targetPrice),
            AlertStatus.ACTIVE,
            Instant.now(),
            null
        );
    }

    public PriceAlert trigger() {
        return new PriceAlert(
            alertId, userId, symbol, condition, targetPrice,
            AlertStatus.TRIGGERED, createdAt, Instant.now()
        );
    }

    /**
     * Check if the alert should trigger based on price movement
     */
    public boolean shouldTrigger(BigDecimal previousPrice, BigDecimal currentPrice) {
        return switch (condition) {
            case CROSSES_ABOVE -> previousPrice.compareTo(targetPrice) <= 0
                               && currentPrice.compareTo(targetPrice) > 0;
            case CROSSES_BELOW -> previousPrice.compareTo(targetPrice) >= 0
                               && currentPrice.compareTo(targetPrice) < 0;
            case CROSSES -> (previousPrice.compareTo(targetPrice) <= 0 && currentPrice.compareTo(targetPrice) > 0)
                         || (previousPrice.compareTo(targetPrice) >= 0 && currentPrice.compareTo(targetPrice) < 0);
        };
    }
}
