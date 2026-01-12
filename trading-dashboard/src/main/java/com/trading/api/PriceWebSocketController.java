package com.trading.api;

import com.trading.model.OhlcCandle;
import com.trading.model.PriceTick;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

/**
 * WebSocket controller for streaming real-time price data to connected clients.
 *
 * Listens to Kafka topics and broadcasts to WebSocket subscribers:
 * - /topic/prices/{symbol} - Live price ticks
 * - /topic/candles/{symbol} - OHLC candles
 * - /topic/prices - All price updates
 */
@Controller
public class PriceWebSocketController {

    private static final Logger log = LoggerFactory.getLogger(PriceWebSocketController.class);

    private final SimpMessagingTemplate messagingTemplate;

    public PriceWebSocketController(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    /**
     * Listen to price ticks from Kafka and broadcast via WebSocket
     */
    @KafkaListener(
            topics = "${trading.kafka.topics.price-ticks}",
            groupId = "websocket-price-broadcaster",
            containerFactory = "priceTickListenerFactory"
    )
    public void broadcastPriceTick(PriceTick tick) {
        // Broadcast to symbol-specific topic
        String destination = "/topic/prices/" + tick.symbol();
        messagingTemplate.convertAndSend(destination, tick);

        // Also broadcast to general prices topic
        messagingTemplate.convertAndSend("/topic/prices", tick);

        log.trace("Broadcast price tick: {} @ {}", tick.symbol(), tick.price());
    }

    /**
     * Listen to OHLC candles from Kafka and broadcast via WebSocket
     */
    @KafkaListener(
            topics = "${trading.kafka.topics.ohlc-candles}",
            groupId = "websocket-candle-broadcaster",
            containerFactory = "ohlcCandleListenerFactory"
    )
    public void broadcastOhlcCandle(OhlcCandle candle) {
        String destination = "/topic/candles/" + candle.symbol();
        messagingTemplate.convertAndSend(destination, candle);

        log.debug("Broadcast OHLC candle: {} O:{} H:{} L:{} C:{}",
                candle.symbol(), candle.open(), candle.high(), candle.low(), candle.close());
    }
}
