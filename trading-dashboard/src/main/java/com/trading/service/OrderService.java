package com.trading.service;

import com.trading.config.TradingProperties;
import com.trading.model.Order;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Service for order management.
 *
 * In production, this would:
 * - Persist orders to database
 * - Integrate with trading engine
 * - Handle position management
 *
 * For demo, uses in-memory storage and publishes to Kafka.
 */
@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final KafkaTemplate<String, Object> kafkaTemplate;
    private final TradingProperties properties;

    // In-memory order storage (use database in production)
    private final Map<String, Order> orders = new ConcurrentHashMap<>();

    public OrderService(KafkaTemplate<String, Object> kafkaTemplate, TradingProperties properties) {
        this.kafkaTemplate = kafkaTemplate;
        this.properties = properties;
    }

    public Order placeOrder(String userId, String symbol, Order.OrderSide side,
                           double quantity, Double price) {

        Order order;
        if (price == null || price == 0) {
            order = Order.createMarketOrder(userId, symbol, side, quantity);
        } else {
            order = Order.createLimitOrder(userId, symbol, side, quantity, price);
        }

        // Store order
        orders.put(order.orderId(), order);

        // Publish to Kafka for processing
        kafkaTemplate.send(
                properties.kafka().topics().orders(),
                symbol,  // Key by symbol for partitioning
                order
        );

        log.info("Order placed: {} {} {} {} @ {}",
                order.orderId(), side, quantity, symbol, price);

        return order;
    }

    public List<Order> getOrdersByUser(String userId) {
        return orders.values().stream()
                .filter(o -> o.userId().equals(userId))
                .collect(Collectors.toList());
    }

    public Order getOrder(String orderId) {
        return orders.get(orderId);
    }

    public boolean cancelOrder(String orderId, String userId) {
        Order order = orders.get(orderId);
        if (order == null || !order.userId().equals(userId)) {
            return false;
        }

        if (order.status() != Order.OrderStatus.PENDING &&
            order.status() != Order.OrderStatus.OPEN) {
            log.warn("Cannot cancel order {} in status {}", orderId, order.status());
            return false;
        }

        Order cancelledOrder = order.withStatus(Order.OrderStatus.CANCELLED);
        orders.put(orderId, cancelledOrder);

        // Publish cancellation event
        kafkaTemplate.send(
                properties.kafka().topics().orders(),
                cancelledOrder.symbol(),
                cancelledOrder
        );

        log.info("Order cancelled: {}", orderId);
        return true;
    }

    public void updateOrderStatus(String orderId, Order.OrderStatus status) {
        Order order = orders.get(orderId);
        if (order != null) {
            orders.put(orderId, order.withStatus(status));
        }
    }
}
