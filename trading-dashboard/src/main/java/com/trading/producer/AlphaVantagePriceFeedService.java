package com.trading.producer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.model.PriceTick;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class AlphaVantagePriceFeedService implements PriceFeedService {

    private static final Logger log = LoggerFactory.getLogger(AlphaVantagePriceFeedService.class);
    private static final String BASE_URL = "https://www.alphavantage.co/query";

    private final RestClient restClient;
    private final ObjectMapper objectMapper;
    private final String apiKey;

    // Rate limiting: 5 requests per minute for free tier
    private final AtomicInteger requestCount = new AtomicInteger(0);
    private final AtomicLong windowStart = new AtomicLong(System.currentTimeMillis());
    private static final int MAX_REQUESTS_PER_MINUTE = 5;

    // Simple cache to reduce API calls
    private final Map<String, CachedPrice> priceCache = new ConcurrentHashMap<>();
    private static final long CACHE_TTL_MS = 60_000; // 1 minute cache

    public AlphaVantagePriceFeedService(
            ObjectMapper objectMapper,
            @Value("${trading.alphavantage.api-key:demo}") String apiKey) {
        this.restClient = RestClient.builder()
                .baseUrl(BASE_URL)
                .build();
        this.objectMapper = objectMapper;
        this.apiKey = apiKey;
    }

    @Override
    public PriceTick getPrice(String symbol) {
        // Check cache first
        CachedPrice cached = priceCache.get(symbol);
        if (cached != null && !cached.isExpired()) {
            log.debug("Cache hit for {}", symbol);
            return cached.tick();
        }

        // Check rate limit
        if (!checkRateLimit()) {
            log.warn("Rate limit exceeded for Alpha Vantage API");
            return null;
        }

        try {
            String response = restClient.get()
                    .uri(uriBuilder -> uriBuilder
                            .queryParam("function", "GLOBAL_QUOTE")
                            .queryParam("symbol", symbol)
                            .queryParam("apikey", apiKey)
                            .build())
                    .retrieve()
                    .body(String.class);

            PriceTick tick = parseGlobalQuote(response, symbol);
            if (tick != null) {
                priceCache.put(symbol, new CachedPrice(tick, System.currentTimeMillis()));
            }
            return tick;

        } catch (RestClientException e) {
            log.error("Failed to fetch price for {}: {}", symbol, e.getMessage());
            return null;
        }
    }

    @Override
    public List<PriceTick> getPrices(List<String> symbols) {
        return symbols.stream()
                .map(this::getPrice)
                .filter(tick -> tick != null)
                .toList();
    }

    @Override
    public boolean isAvailable() {
        return checkRateLimit();
    }

    @Override
    public String getSourceName() {
        return "Alpha Vantage API";
    }

    private PriceTick parseGlobalQuote(String response, String symbol) {
        try {
            JsonNode root = objectMapper.readTree(response);
            JsonNode quote = root.get("Global Quote");

            if (quote == null || quote.isEmpty()) {
                // Check for rate limit message
                JsonNode note = root.get("Note");
                if (note != null) {
                    log.warn("Alpha Vantage rate limit: {}", note.asText());
                }
                return null;
            }

            BigDecimal price = new BigDecimal(quote.get("05. price").asText());
            BigDecimal open = new BigDecimal(quote.get("02. open").asText());
            BigDecimal high = new BigDecimal(quote.get("03. high").asText());
            BigDecimal low = new BigDecimal(quote.get("04. low").asText());
            long volume = quote.get("06. volume").asLong();

            // Approximate bid/ask from last price
            BigDecimal spread = price.multiply(BigDecimal.valueOf(0.001)); // 0.1% spread
            BigDecimal bid = price.subtract(spread);
            BigDecimal ask = price.add(spread);

            return new PriceTick(
                    symbol,
                    price,
                    bid,
                    ask,
                    volume,
                    Instant.now(),
                    "ALPHA_VANTAGE"
            );

        } catch (Exception e) {
            log.error("Failed to parse Alpha Vantage response for {}: {}", symbol, e.getMessage());
            return null;
        }
    }

    private synchronized boolean checkRateLimit() {
        long now = System.currentTimeMillis();
        long windowStartTime = windowStart.get();

        // Reset window every minute
        if (now - windowStartTime > 60_000) {
            windowStart.set(now);
            requestCount.set(0);
        }

        if (requestCount.get() >= MAX_REQUESTS_PER_MINUTE) {
            return false;
        }

        requestCount.incrementAndGet();
        return true;
    }

    private record CachedPrice(PriceTick tick, long timestamp) {
        boolean isExpired() {
            return System.currentTimeMillis() - timestamp > CACHE_TTL_MS;
        }
    }
}
