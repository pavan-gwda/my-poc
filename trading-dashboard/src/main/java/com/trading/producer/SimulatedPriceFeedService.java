package com.trading.producer;

import com.trading.model.PriceTick;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Simulates realistic stock price movements using Geometric Brownian Motion.
 * This is the same model used in options pricing (Black-Scholes).
 */
@Service
public class SimulatedPriceFeedService implements PriceFeedService {

    private static final Logger log = LoggerFactory.getLogger(SimulatedPriceFeedService.class);
    private final Random random = new Random();

    // Track current simulated prices
    private final Map<String, SimulatedStock> stocks = new ConcurrentHashMap<>();

    // Initial prices for common stocks (starting point for simulation)
    private static final Map<String, Double> INITIAL_PRICES = Map.of(
            "AAPL", 175.00,
            "GOOGL", 140.00,
            "MSFT", 375.00,
            "AMZN", 180.00,
            "TSLA", 250.00,
            "META", 500.00,
            "NVDA", 480.00,
            "JPM", 195.00,
            "V", 280.00,
            "JNJ", 155.00
    );

    public SimulatedPriceFeedService() {
        // Initialize all stocks
        INITIAL_PRICES.forEach((symbol, price) ->
                stocks.put(symbol, new SimulatedStock(symbol, price)));
    }

    @Override
    public PriceTick getPrice(String symbol) {
        SimulatedStock stock = stocks.computeIfAbsent(symbol,
                s -> new SimulatedStock(s, 100.0 + random.nextDouble() * 200)); // Random initial price

        return stock.nextTick();
    }

    @Override
    public List<PriceTick> getPrices(List<String> symbols) {
        return symbols.stream()
                .map(this::getPrice)
                .toList();
    }

    @Override
    public boolean isAvailable() {
        return true; // Simulator is always available
    }

    @Override
    public String getSourceName() {
        return "Price Simulator (GBM)";
    }

    /**
     * Simulates a single stock using Geometric Brownian Motion
     */
    private class SimulatedStock {
        private final String symbol;
        private double currentPrice;
        private long cumulativeVolume = 0;

        // GBM parameters
        private static final double DRIFT = 0.0001;      // μ (mu) - expected return
        private static final double VOLATILITY = 0.02;   // σ (sigma) - standard deviation
        private static final double DT = 1.0 / 252;      // Time step (1 trading day / 252 days per year)

        SimulatedStock(String symbol, double initialPrice) {
            this.symbol = symbol;
            this.currentPrice = initialPrice;
        }

        synchronized PriceTick nextTick() {
            // Geometric Brownian Motion formula:
            // dS = μ*S*dt + σ*S*dW
            // where dW is a Wiener process (random walk)

            double randomShock = random.nextGaussian();
            double drift = DRIFT * currentPrice * DT;
            double diffusion = VOLATILITY * currentPrice * Math.sqrt(DT) * randomShock;

            currentPrice = Math.max(0.01, currentPrice + drift + diffusion);

            // Simulate bid-ask spread (0.01% to 0.1% based on volatility)
            double spreadPercent = 0.0001 + (Math.abs(randomShock) * 0.0005);
            double halfSpread = currentPrice * spreadPercent;

            BigDecimal price = BigDecimal.valueOf(currentPrice).setScale(2, RoundingMode.HALF_UP);
            BigDecimal bid = BigDecimal.valueOf(currentPrice - halfSpread).setScale(2, RoundingMode.HALF_UP);
            BigDecimal ask = BigDecimal.valueOf(currentPrice + halfSpread).setScale(2, RoundingMode.HALF_UP);

            // Simulate volume (higher when price moves more)
            long tickVolume = (long) (100 + Math.abs(randomShock) * 1000);
            cumulativeVolume += tickVolume;

            return new PriceTick(
                    symbol,
                    price,
                    bid,
                    ask,
                    tickVolume,
                    Instant.now(),
                    "SIMULATOR"
            );
        }
    }

    /**
     * Get all available simulated symbols
     */
    public List<String> getAvailableSymbols() {
        return List.copyOf(INITIAL_PRICES.keySet());
    }
}
