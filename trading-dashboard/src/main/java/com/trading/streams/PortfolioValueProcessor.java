package com.trading.streams;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.config.TradingProperties;
import com.trading.model.Portfolio;
import com.trading.model.PriceTick;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.support.serializer.JsonSerde;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Kafka Streams processor for real-time portfolio valuation.
 *
 * Architecture:
 * - Price ticks (KStream) joined with Holdings (GlobalKTable)
 * - On each price update, recalculate affected portfolio values
 * - Emit portfolio updates to downstream topic
 *
 * Why GlobalKTable for holdings?
 * - Holdings data is relatively small per user
 * - Need to access holdings from any partition (prices partitioned by symbol)
 * - GlobalKTable replicates to all instances
 */
@Component
public class PortfolioValueProcessor {

    private static final Logger log = LoggerFactory.getLogger(PortfolioValueProcessor.class);

    private final TradingProperties properties;
    private final ObjectMapper objectMapper;

    public PortfolioValueProcessor(TradingProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @Autowired
    public void buildPipeline(StreamsBuilder streamsBuilder) {
        // Serdes
        Serde<PriceTick> priceTickSerde = new JsonSerde<>(PriceTick.class, objectMapper);
        Serde<UserHoldings> holdingsSerde = new JsonSerde<>(UserHoldings.class, objectMapper);
        Serde<PortfolioUpdate> portfolioUpdateSerde = new JsonSerde<>(PortfolioUpdate.class, objectMapper);

        // Read holdings as GlobalKTable (keyed by symbol for join)
        // In real system, this would come from a holdings-by-symbol topic
        GlobalKTable<String, UserHoldings> holdingsBySymbol = streamsBuilder
                .globalTable(
                        properties.kafka().topics().holdingsBySymbol(),
                        Consumed.with(Serdes.String(), holdingsSerde),
                        Materialized.as("holdings-store")
                );

        // Price ticks stream
        KStream<String, PriceTick> priceTicks = streamsBuilder
                .stream(
                        properties.kafka().topics().priceTicks(),
                        Consumed.with(Serdes.String(), priceTickSerde)
                );

        // Join price ticks with holdings
        // When price changes for a symbol, look up who holds it and update their portfolio
        KStream<String, PortfolioUpdate> portfolioUpdates = priceTicks
                .join(
                        holdingsBySymbol,
                        // Key mapper: extract symbol from price tick to match holdings
                        (symbol, priceTick) -> symbol,
                        // Value joiner: combine price with holdings to create update
                        (priceTick, holdings) -> calculatePortfolioUpdate(priceTick, holdings)
                )
                .filter((symbol, update) -> update != null);

        // Rekey by userId for downstream processing
        KStream<String, PortfolioUpdate> portfolioUpdatesByUser = portfolioUpdates
                .selectKey((symbol, update) -> update.userId());

        // Output to portfolio updates topic
        portfolioUpdatesByUser
                .peek((userId, update) -> log.debug(
                        "Portfolio update for user {}: {} {} shares @ {} = {}",
                        userId, update.symbol(), update.quantity(), update.currentPrice(), update.marketValue()
                ))
                .to(
                        properties.kafka().topics().portfolioUpdates(),
                        Produced.with(Serdes.String(), portfolioUpdateSerde)
                );

        log.info("Portfolio value processor pipeline built successfully");
    }

    /**
     * Calculate portfolio update when price changes
     */
    private PortfolioUpdate calculatePortfolioUpdate(PriceTick tick, UserHoldings holdings) {
        if (holdings == null || holdings.positions().isEmpty()) {
            return null;
        }

        // Calculate total value for all users holding this symbol
        // In a real system, we'd emit one update per user
        // Simplified: emit for first user in holdings
        for (var entry : holdings.positions().entrySet()) {
            String userId = entry.getKey();
            Position position = entry.getValue();

            BigDecimal marketValue = tick.price().multiply(position.quantity());
            BigDecimal costBasis = position.averageCost().multiply(position.quantity());
            BigDecimal unrealizedPnL = marketValue.subtract(costBasis);

            return new PortfolioUpdate(
                    userId,
                    tick.symbol(),
                    position.quantity(),
                    position.averageCost(),
                    tick.price(),
                    marketValue,
                    unrealizedPnL,
                    Instant.now()
            );
        }

        return null;
    }

    /**
     * Holdings for a specific symbol, keyed by userId
     */
    public record UserHoldings(
            String symbol,
            Map<String, Position> positions // userId -> position
    ) {
        public UserHoldings {
            if (positions == null) {
                positions = new HashMap<>();
            }
        }
    }

    /**
     * Individual position in a symbol
     */
    public record Position(
            BigDecimal quantity,
            BigDecimal averageCost
    ) {}

    /**
     * Portfolio value update event
     */
    public record PortfolioUpdate(
            String userId,
            String symbol,
            BigDecimal quantity,
            BigDecimal averageCost,
            BigDecimal currentPrice,
            BigDecimal marketValue,
            BigDecimal unrealizedPnL,
            Instant timestamp
    ) {}
}
