package com.trading.model;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record Order(
    String orderId,
    String userId,
    String symbol,
    OrderType type,
    OrderSide side,
    BigDecimal quantity,
    BigDecimal price,          // Limit price (null for market orders)
    OrderStatus status,
    Instant createdAt,
    Instant updatedAt,
    BigDecimal filledQuantity,
    BigDecimal averagePrice
) {
    public enum OrderType {
        MARKET,    // Execute immediately at current price
        LIMIT,     // Execute only at specified price or better
        STOP,      // Becomes market order when stop price is reached
        STOP_LIMIT // Becomes limit order when stop price is reached
    }

    public enum OrderSide {
        BUY,
        SELL
    }

    public enum OrderStatus {
        PENDING,      // Order received, not yet processed
        OPEN,         // Order is active in the order book
        PARTIALLY_FILLED,
        FILLED,       // Completely executed
        CANCELLED,
        REJECTED,
        EXPIRED
    }

    public static Order createMarketOrder(String userId, String symbol, OrderSide side, double quantity) {
        return new Order(
            UUID.randomUUID().toString(),
            userId,
            symbol,
            OrderType.MARKET,
            side,
            BigDecimal.valueOf(quantity),
            null,
            OrderStatus.PENDING,
            Instant.now(),
            Instant.now(),
            BigDecimal.ZERO,
            BigDecimal.ZERO
        );
    }

    public static Order createLimitOrder(String userId, String symbol, OrderSide side,
                                         double quantity, double price) {
        return new Order(
            UUID.randomUUID().toString(),
            userId,
            symbol,
            OrderType.LIMIT,
            side,
            BigDecimal.valueOf(quantity),
            BigDecimal.valueOf(price),
            OrderStatus.PENDING,
            Instant.now(),
            Instant.now(),
            BigDecimal.ZERO,
            BigDecimal.ZERO
        );
    }

    public Order withStatus(OrderStatus newStatus) {
        return new Order(
            orderId, userId, symbol, type, side, quantity, price,
            newStatus, createdAt, Instant.now(), filledQuantity, averagePrice
        );
    }

    public Order filled(BigDecimal filledQty, BigDecimal avgPrice) {
        return new Order(
            orderId, userId, symbol, type, side, quantity, price,
            OrderStatus.FILLED, createdAt, Instant.now(), filledQty, avgPrice
        );
    }
}
