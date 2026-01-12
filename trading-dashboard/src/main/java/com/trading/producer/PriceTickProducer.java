package com.trading.producer;

import com.trading.config.TradingProperties;
import com.trading.model.PriceTick;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Produces price ticks to Kafka at regular intervals.
 * Uses Alpha Vantage when available, falls back to simulator.
 */
@Component
public class PriceTickProducer {

    private static final Logger log = LoggerFactory.getLogger(PriceTickProducer.class);

    private final KafkaTemplate<String, Object> kafkaTemplate;
    private final AlphaVantagePriceFeedService alphaVantageService;
    private final SimulatedPriceFeedService simulatorService;
    private final String priceTopic;

    // Symbols to track
    private final List<String> symbols = List.of(
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
            "META", "NVDA", "JPM", "V", "JNJ"
    );

    // Metrics
    private final AtomicLong ticksProduced = new AtomicLong(0);
    private final AtomicLong ticksFailed = new AtomicLong(0);

    public PriceTickProducer(
            KafkaTemplate<String, Object> kafkaTemplate,
            AlphaVantagePriceFeedService alphaVantageService,
            SimulatedPriceFeedService simulatorService,
            TradingProperties properties) {
        this.kafkaTemplate = kafkaTemplate;
        this.alphaVantageService = alphaVantageService;
        this.simulatorService = simulatorService;
        this.priceTopic = properties.kafka().topics().priceTicks();
    }

    /**
     * Produce price ticks every 500ms (2 ticks per second per symbol)
     */
    @Scheduled(fixedRate = 500)
    public void producePriceTicks() {
        for (String symbol : symbols) {
            PriceTick tick = fetchPrice(symbol);
            if (tick != null) {
                publishTick(tick);
            }
        }
    }

    /**
     * Fetch price with fallback strategy
     */
    private PriceTick fetchPrice(String symbol) {
        // Try Alpha Vantage first if available
        if (alphaVantageService.isAvailable()) {
            PriceTick tick = alphaVantageService.getPrice(symbol);
            if (tick != null) {
                return tick;
            }
        }

        // Fallback to simulator
        return simulatorService.getPrice(symbol);
    }

    /**
     * Publish tick to Kafka with proper error handling
     */
    private void publishTick(PriceTick tick) {
        // Use symbol as key for partitioning - ensures all ticks for same symbol
        // go to same partition, maintaining order
        CompletableFuture<SendResult<String, Object>> future =
                kafkaTemplate.send(priceTopic, tick.symbol(), tick);

        future.whenComplete((result, ex) -> {
            if (ex != null) {
                ticksFailed.incrementAndGet();
                log.error("Failed to send tick for {}: {}", tick.symbol(), ex.getMessage());
            } else {
                ticksProduced.incrementAndGet();
                log.debug("Sent tick: {} @ {} to partition {}",
                        tick.symbol(),
                        tick.price(),
                        result.getRecordMetadata().partition());
            }
        });
    }

    /**
     * Manually produce a tick for a specific symbol (for testing/API)
     */
    public void produceTickForSymbol(String symbol) {
        PriceTick tick = fetchPrice(symbol);
        if (tick != null) {
            publishTick(tick);
        }
    }

    /**
     * Get production metrics
     */
    public ProducerMetrics getMetrics() {
        return new ProducerMetrics(
                ticksProduced.get(),
                ticksFailed.get(),
                symbols.size()
        );
    }

    public record ProducerMetrics(
            long ticksProduced,
            long ticksFailed,
            int symbolCount
    ) {}
}
