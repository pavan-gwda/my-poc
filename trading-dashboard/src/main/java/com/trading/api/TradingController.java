package com.trading.api;

import com.trading.model.Order;
import com.trading.model.PriceAlert;
import com.trading.model.PriceTick;
import com.trading.producer.PriceTickProducer;
import com.trading.producer.SimulatedPriceFeedService;
import com.trading.service.OrderService;
import com.trading.service.AlertService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for trading operations.
 *
 * Endpoints:
 * - GET /api/prices - Get current prices
 * - POST /api/orders - Place new order
 * - GET /api/orders/{userId} - Get user orders
 * - POST /api/alerts - Create price alert
 * - GET /api/alerts/{userId} - Get user alerts
 * - GET /api/metrics - Producer metrics
 */
@RestController
@RequestMapping("/api")
public class TradingController {

    private static final Logger log = LoggerFactory.getLogger(TradingController.class);

    private final PriceTickProducer priceTickProducer;
    private final SimulatedPriceFeedService priceFeedService;
    private final OrderService orderService;
    private final AlertService alertService;

    public TradingController(
            PriceTickProducer priceTickProducer,
            SimulatedPriceFeedService priceFeedService,
            OrderService orderService,
            AlertService alertService) {
        this.priceTickProducer = priceTickProducer;
        this.priceFeedService = priceFeedService;
        this.orderService = orderService;
        this.alertService = alertService;
    }

    // ==================== PRICE ENDPOINTS ====================

    @GetMapping("/prices")
    public ResponseEntity<List<PriceTick>> getCurrentPrices() {
        List<String> symbols = priceFeedService.getAvailableSymbols();
        List<PriceTick> prices = priceFeedService.getPrices(symbols);
        return ResponseEntity.ok(prices);
    }

    @GetMapping("/prices/{symbol}")
    public ResponseEntity<PriceTick> getPrice(@PathVariable String symbol) {
        PriceTick price = priceFeedService.getPrice(symbol.toUpperCase());
        if (price == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(price);
    }

    // ==================== ORDER ENDPOINTS ====================

    @PostMapping("/orders")
    public ResponseEntity<Order> placeOrder(@Valid @RequestBody OrderRequest request) {
        log.info("Received order request: {} {} {} @ {}",
                request.side(), request.quantity(), request.symbol(), request.price());

        Order order = orderService.placeOrder(
                request.userId(),
                request.symbol(),
                request.side(),
                request.quantity(),
                request.price()
        );

        return ResponseEntity.ok(order);
    }

    @GetMapping("/orders/{userId}")
    public ResponseEntity<List<Order>> getUserOrders(@PathVariable String userId) {
        List<Order> orders = orderService.getOrdersByUser(userId);
        return ResponseEntity.ok(orders);
    }

    @DeleteMapping("/orders/{orderId}")
    public ResponseEntity<Void> cancelOrder(
            @PathVariable String orderId,
            @RequestParam String userId) {
        boolean cancelled = orderService.cancelOrder(orderId, userId);
        if (cancelled) {
            return ResponseEntity.ok().build();
        }
        return ResponseEntity.notFound().build();
    }

    // ==================== ALERT ENDPOINTS ====================

    @PostMapping("/alerts")
    public ResponseEntity<PriceAlert> createAlert(@Valid @RequestBody AlertRequest request) {
        log.info("Creating alert for user {}: {} {} {}",
                request.userId(), request.symbol(), request.condition(), request.targetPrice());

        PriceAlert alert = alertService.createAlert(
                request.userId(),
                request.symbol(),
                request.condition(),
                request.targetPrice()
        );

        return ResponseEntity.ok(alert);
    }

    @GetMapping("/alerts/{userId}")
    public ResponseEntity<List<PriceAlert>> getUserAlerts(@PathVariable String userId) {
        List<PriceAlert> alerts = alertService.getAlertsByUser(userId);
        return ResponseEntity.ok(alerts);
    }

    @DeleteMapping("/alerts/{alertId}")
    public ResponseEntity<Void> cancelAlert(
            @PathVariable String alertId,
            @RequestParam String userId) {
        boolean cancelled = alertService.cancelAlert(alertId, userId);
        if (cancelled) {
            return ResponseEntity.ok().build();
        }
        return ResponseEntity.notFound().build();
    }

    // ==================== METRICS ENDPOINTS ====================

    @GetMapping("/metrics/producer")
    public ResponseEntity<PriceTickProducer.ProducerMetrics> getProducerMetrics() {
        return ResponseEntity.ok(priceTickProducer.getMetrics());
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "trading-dashboard"
        ));
    }

    // ==================== REQUEST DTOs ====================

    public record OrderRequest(
            @NotBlank String userId,
            @NotBlank String symbol,
            Order.OrderSide side,
            @Positive double quantity,
            Double price // null for market orders
    ) {}

    public record AlertRequest(
            @NotBlank String userId,
            @NotBlank String symbol,
            PriceAlert.AlertCondition condition,
            @Positive double targetPrice
    ) {}
}
