package com.ai.agent.tools;

import dev.langchain4j.agent.tool.Tool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;

/**
 * Database query tool for the AI agent.
 *
 * Simulates a product/inventory database.
 * In production, this would execute real SQL queries.
 *
 * KEY CONCEPT: The agent learns to query data based on natural language!
 */
@Component
public class DatabaseTool {

    private static final Logger log = LoggerFactory.getLogger(DatabaseTool.class);

    // Simulated product database
    private static final List<Map<String, Object>> PRODUCTS = List.of(
            Map.of("id", 1, "name", "Laptop", "category", "Electronics", "price", 999.99, "stock", 50),
            Map.of("id", 2, "name", "Smartphone", "category", "Electronics", "price", 699.99, "stock", 120),
            Map.of("id", 3, "name", "Headphones", "category", "Electronics", "price", 149.99, "stock", 200),
            Map.of("id", 4, "name", "Coffee Maker", "category", "Appliances", "price", 79.99, "stock", 75),
            Map.of("id", 5, "name", "Desk Chair", "category", "Furniture", "price", 249.99, "stock", 30),
            Map.of("id", 6, "name", "Monitor", "category", "Electronics", "price", 399.99, "stock", 45),
            Map.of("id", 7, "name", "Keyboard", "category", "Electronics", "price", 89.99, "stock", 150),
            Map.of("id", 8, "name", "Mouse", "category", "Electronics", "price", 49.99, "stock", 180)
    );

    // Simulated orders
    private static final List<Map<String, Object>> ORDERS = List.of(
            Map.of("orderId", "ORD-001", "productId", 1, "quantity", 2, "customer", "John Doe", "total", 1999.98),
            Map.of("orderId", "ORD-002", "productId", 2, "quantity", 1, "customer", "Jane Smith", "total", 699.99),
            Map.of("orderId", "ORD-003", "productId", 3, "quantity", 3, "customer", "Bob Wilson", "total", 449.97),
            Map.of("orderId", "ORD-004", "productId", 6, "quantity", 2, "customer", "Alice Brown", "total", 799.98),
            Map.of("orderId", "ORD-005", "productId", 1, "quantity", 1, "customer", "Charlie Davis", "total", 999.99)
    );

    @Tool("Get all products in the database. Returns list of products with id, name, category, price, and stock.")
    public String getAllProducts() {
        log.info("TOOL CALLED: getAllProducts()");
        return formatProducts(PRODUCTS);
    }

    @Tool("Search for products by name. Use when user asks about a specific product.")
    public String searchProductByName(String name) {
        log.info("TOOL CALLED: searchProductByName({})", name);

        List<Map<String, Object>> results = PRODUCTS.stream()
                .filter(p -> p.get("name").toString().toLowerCase().contains(name.toLowerCase()))
                .toList();

        if (results.isEmpty()) {
            return "No products found matching: " + name;
        }
        return formatProducts(results);
    }

    @Tool("Get products by category. Categories: Electronics, Appliances, Furniture")
    public String getProductsByCategory(String category) {
        log.info("TOOL CALLED: getProductsByCategory({})", category);

        List<Map<String, Object>> results = PRODUCTS.stream()
                .filter(p -> p.get("category").toString().equalsIgnoreCase(category))
                .toList();

        if (results.isEmpty()) {
            return "No products found in category: " + category;
        }
        return formatProducts(results);
    }

    @Tool("Get products within a price range. Provide minimum and maximum price.")
    public String getProductsByPriceRange(double minPrice, double maxPrice) {
        log.info("TOOL CALLED: getProductsByPriceRange({}, {})", minPrice, maxPrice);

        List<Map<String, Object>> results = PRODUCTS.stream()
                .filter(p -> {
                    double price = (double) p.get("price");
                    return price >= minPrice && price <= maxPrice;
                })
                .toList();

        if (results.isEmpty()) {
            return String.format("No products found between $%.2f and $%.2f", minPrice, maxPrice);
        }
        return formatProducts(results);
    }

    @Tool("Check stock level for a specific product by product ID.")
    public String checkStock(int productId) {
        log.info("TOOL CALLED: checkStock({})", productId);

        return PRODUCTS.stream()
                .filter(p -> (int) p.get("id") == productId)
                .findFirst()
                .map(p -> String.format("Product '%s' has %d units in stock",
                        p.get("name"), p.get("stock")))
                .orElse("Product not found with ID: " + productId);
    }

    @Tool("Get total inventory value (sum of price * stock for all products)")
    public String getTotalInventoryValue() {
        log.info("TOOL CALLED: getTotalInventoryValue()");

        double totalValue = PRODUCTS.stream()
                .mapToDouble(p -> (double) p.get("price") * (int) p.get("stock"))
                .sum();

        return String.format("Total inventory value: $%.2f", totalValue);
    }

    @Tool("Get recent orders. Shows order ID, product, customer, and total.")
    public String getRecentOrders() {
        log.info("TOOL CALLED: getRecentOrders()");

        StringBuilder sb = new StringBuilder("Recent Orders:\n");
        for (Map<String, Object> order : ORDERS) {
            int productId = (int) order.get("productId");
            String productName = PRODUCTS.stream()
                    .filter(p -> (int) p.get("id") == productId)
                    .map(p -> (String) p.get("name"))
                    .findFirst()
                    .orElse("Unknown");

            sb.append(String.format("  %s: %s x%d for %s - $%.2f\n",
                    order.get("orderId"),
                    productName,
                    order.get("quantity"),
                    order.get("customer"),
                    order.get("total")));
        }
        return sb.toString();
    }

    private String formatProducts(List<Map<String, Object>> products) {
        StringBuilder sb = new StringBuilder("Products:\n");
        for (Map<String, Object> p : products) {
            sb.append(String.format("  [%d] %s (%s) - $%.2f - Stock: %d\n",
                    p.get("id"), p.get("name"), p.get("category"),
                    p.get("price"), p.get("stock")));
        }
        return sb.toString();
    }
}
