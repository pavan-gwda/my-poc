package com.trading.model;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;

public record Portfolio(
    String portfolioId,
    String userId,
    Map<String, Holding> holdings,    // symbol -> holding
    BigDecimal totalValue,            // Current total value
    BigDecimal totalCost,             // Total cost basis
    BigDecimal dayPnL,                // Profit/Loss for the day
    BigDecimal totalPnL,              // Total profit/loss
    Instant lastUpdated
) {
    public record Holding(
        String symbol,
        BigDecimal quantity,
        BigDecimal averageCost,       // Average purchase price
        BigDecimal currentPrice,
        BigDecimal marketValue,       // quantity * currentPrice
        BigDecimal unrealizedPnL      // marketValue - (quantity * averageCost)
    ) {
        public static Holding create(String symbol, double qty, double avgCost, double currentPrice) {
            BigDecimal quantity = BigDecimal.valueOf(qty);
            BigDecimal avgCostBd = BigDecimal.valueOf(avgCost);
            BigDecimal currPrice = BigDecimal.valueOf(currentPrice);
            BigDecimal marketValue = quantity.multiply(currPrice);
            BigDecimal costBasis = quantity.multiply(avgCostBd);

            return new Holding(
                symbol,
                quantity,
                avgCostBd,
                currPrice,
                marketValue,
                marketValue.subtract(costBasis)
            );
        }

        public Holding withUpdatedPrice(BigDecimal newPrice) {
            BigDecimal newMarketValue = quantity.multiply(newPrice);
            BigDecimal costBasis = quantity.multiply(averageCost);
            return new Holding(
                symbol,
                quantity,
                averageCost,
                newPrice,
                newMarketValue,
                newMarketValue.subtract(costBasis)
            );
        }
    }
}
