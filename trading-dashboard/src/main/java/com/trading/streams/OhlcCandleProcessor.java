package com.trading.streams;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.config.TradingProperties;
import com.trading.model.OhlcCandle;
import com.trading.model.PriceTick;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.state.WindowStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.support.serializer.JsonSerde;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;

/**
 * Kafka Streams processor that aggregates price ticks into OHLC candlesticks.
 *
 * Input: stock-price-ticks topic
 * Output: stock-ohlc-candles topic
 *
 * Creates 1-minute tumbling windows for each stock symbol.
 */
@Component
public class OhlcCandleProcessor {

    private static final Logger log = LoggerFactory.getLogger(OhlcCandleProcessor.class);

    private final TradingProperties properties;
    private final ObjectMapper objectMapper;

    // Window configuration
    private static final Duration WINDOW_SIZE = Duration.ofMinutes(1);
    private static final Duration GRACE_PERIOD = Duration.ofSeconds(30); // Allow late events

    public OhlcCandleProcessor(TradingProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @Autowired
    public void buildPipeline(StreamsBuilder streamsBuilder) {
        // Create Serdes for our domain objects
        Serde<PriceTick> priceTickSerde = new JsonSerde<>(PriceTick.class, objectMapper);
        Serde<OhlcCandle> ohlcCandleSerde = new JsonSerde<>(OhlcCandle.class, objectMapper);
        Serde<OhlcAggregator> aggregatorSerde = new JsonSerde<>(OhlcAggregator.class, objectMapper);

        // Read from price ticks topic
        KStream<String, PriceTick> priceTicks = streamsBuilder
                .stream(
                        properties.kafka().topics().priceTicks(),
                        Consumed.with(Serdes.String(), priceTickSerde)
                                .withTimestampExtractor(new PriceTickTimestampExtractor())
                );

        // Group by symbol (key) and apply tumbling window aggregation
        KTable<Windowed<String>, OhlcCandle> ohlcCandles = priceTicks
                // Group by symbol (already the key)
                .groupByKey(Grouped.with(Serdes.String(), priceTickSerde))
                // Apply tumbling window
                .windowedBy(TimeWindows.ofSizeAndGrace(WINDOW_SIZE, GRACE_PERIOD))
                // Aggregate into OHLC candles
                .aggregate(
                        // Initializer
                        OhlcAggregator::new,
                        // Aggregator
                        (symbol, tick, aggregator) -> aggregator.add(tick),
                        // Materialized state store
                        Materialized.<String, OhlcAggregator, WindowStore<Bytes, byte[]>>as("ohlc-store")
                                .withKeySerde(Serdes.String())
                                .withValueSerde(aggregatorSerde)
                )
                // Convert aggregator to final OHLC candle
                .mapValues((windowedKey, aggregator) -> aggregator.toCandle(
                        windowedKey.key(),
                        windowedKey.window().startTime(),
                        windowedKey.window().endTime()
                ));

        // Output to OHLC candles topic
        ohlcCandles
                .toStream()
                .selectKey((windowedKey, candle) -> windowedKey.key()) // Remove window from key
                .peek((symbol, candle) -> log.debug(
                        "OHLC Candle: {} O:{} H:{} L:{} C:{} V:{} Window:[{}-{}]",
                        symbol, candle.open(), candle.high(), candle.low(), candle.close(),
                        candle.volume(), candle.windowStart(), candle.windowEnd()
                ))
                .to(
                        properties.kafka().topics().ohlcCandles(),
                        Produced.with(Serdes.String(), ohlcCandleSerde)
                );

        log.info("OHLC Candle processor pipeline built successfully");
    }

    /**
     * Intermediate aggregator for OHLC calculation.
     * Tracks running state during the window.
     */
    public static class OhlcAggregator {
        private BigDecimal open;
        private BigDecimal high;
        private BigDecimal low;
        private BigDecimal close;
        private long volume;
        private boolean initialized;

        public OhlcAggregator() {
            this.initialized = false;
            this.volume = 0;
        }

        public OhlcAggregator add(PriceTick tick) {
            if (!initialized) {
                // First tick in window sets the open price
                this.open = tick.price();
                this.high = tick.price();
                this.low = tick.price();
                this.initialized = true;
            } else {
                // Update high and low
                if (tick.price().compareTo(high) > 0) {
                    this.high = tick.price();
                }
                if (tick.price().compareTo(low) < 0) {
                    this.low = tick.price();
                }
            }

            // Always update close and accumulate volume
            this.close = tick.price();
            this.volume += tick.volume();

            return this;
        }

        public OhlcCandle toCandle(String symbol, Instant windowStart, Instant windowEnd) {
            return new OhlcCandle(
                    symbol,
                    open != null ? open : BigDecimal.ZERO,
                    high != null ? high : BigDecimal.ZERO,
                    low != null ? low : BigDecimal.ZERO,
                    close != null ? close : BigDecimal.ZERO,
                    volume,
                    windowStart,
                    windowEnd,
                    "1m"
            );
        }

        // Getters needed for JSON serialization
        public BigDecimal getOpen() { return open; }
        public BigDecimal getHigh() { return high; }
        public BigDecimal getLow() { return low; }
        public BigDecimal getClose() { return close; }
        public long getVolume() { return volume; }
        public boolean isInitialized() { return initialized; }

        // Setters needed for JSON deserialization
        public void setOpen(BigDecimal open) { this.open = open; }
        public void setHigh(BigDecimal high) { this.high = high; }
        public void setLow(BigDecimal low) { this.low = low; }
        public void setClose(BigDecimal close) { this.close = close; }
        public void setVolume(long volume) { this.volume = volume; }
        public void setInitialized(boolean initialized) { this.initialized = initialized; }
    }
}
