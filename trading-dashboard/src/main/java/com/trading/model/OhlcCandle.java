package com.trading.model;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * OHLC (Open-High-Low-Close) Candlestick representation.
 * Used for charting and technical analysis.
 */
public record OhlcCandle(
    String symbol,
    BigDecimal open,         // First price in the window
    BigDecimal high,         // Highest price in the window
    BigDecimal low,          // Lowest price in the window
    BigDecimal close,        // Last price in the window
    long volume,             // Total volume in the window
    Instant windowStart,     // Start of the time window
    Instant windowEnd,       // End of the time window
    String interval          // e.g., "1m", "5m", "1h"
) {
    /**
     * Creates a new candle from a single price tick (initial state)
     */
    public static OhlcCandle fromTick(PriceTick tick, Instant windowStart, Instant windowEnd, String interval) {
        return new OhlcCandle(
            tick.symbol(),
            tick.price(),
            tick.price(),
            tick.price(),
            tick.price(),
            tick.volume(),
            windowStart,
            windowEnd,
            interval
        );
    }

    /**
     * Aggregates a new price tick into this candle
     */
    public OhlcCandle aggregate(PriceTick tick) {
        return new OhlcCandle(
            this.symbol,
            this.open,                                              // Open stays the same
            this.high.max(tick.price()),                           // Update high if needed
            this.low.min(tick.price()),                            // Update low if needed
            tick.price(),                                          // Close is always latest
            this.volume + tick.volume(),                           // Accumulate volume
            this.windowStart,
            this.windowEnd,
            this.interval
        );
    }
}
