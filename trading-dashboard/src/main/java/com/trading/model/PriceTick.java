package com.trading.model;

import java.math.BigDecimal;
import java.time.Instant;

public record PriceTick(
    String symbol,           // e.g., "AAPL", "GOOGL"
    BigDecimal price,        // Current price
    BigDecimal bid,          // Best bid price
    BigDecimal ask,          // Best ask price
    long volume,             // Volume in this tick
    Instant timestamp,       // When this tick occurred
    String exchange          // e.g., "NASDAQ", "NYSE"
) {
    public static PriceTick of(String symbol, double price, long volume) {
        BigDecimal p = BigDecimal.valueOf(price);
        return new PriceTick(
            symbol,
            p,
            p.subtract(BigDecimal.valueOf(0.01)),
            p.add(BigDecimal.valueOf(0.01)),
            volume,
            Instant.now(),
            "NASDAQ"
        );
    }
}
