package com.trading.producer;

import com.trading.model.PriceTick;

import java.util.List;

/**
 * Strategy interface for fetching price data.
 * Allows swapping between real API and simulator.
 */
public interface PriceFeedService {

    /**
     * Fetch current price for a single symbol
     */
    PriceTick getPrice(String symbol);

    /**
     * Fetch current prices for multiple symbols
     */
    List<PriceTick> getPrices(List<String> symbols);

    /**
     * Check if the service is available
     */
    boolean isAvailable();

    /**
     * Get the source name for logging/debugging
     */
    String getSourceName();
}
