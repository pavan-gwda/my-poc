package com.trading.streams;

import com.trading.model.PriceTick;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.streams.processor.TimestampExtractor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Custom timestamp extractor that uses the event time from PriceTick.
 *
 * Why custom extractor?
 * - Kafka default uses record timestamp (when producer sent it)
 * - For accurate windowing, we need the actual event time (when price was quoted)
 * - This is crucial for financial data where milliseconds matter
 *
 * Event Time vs Processing Time:
 * - Event Time: When the event actually happened (tick.timestamp())
 * - Processing Time: When the system processes it (Kafka record timestamp)
 *
 * For financial data, EVENT TIME is always preferred.
 */
public class PriceTickTimestampExtractor implements TimestampExtractor {

    private static final Logger log = LoggerFactory.getLogger(PriceTickTimestampExtractor.class);

    @Override
    public long extract(ConsumerRecord<Object, Object> record, long partitionTime) {
        if (record.value() instanceof PriceTick tick) {
            if (tick.timestamp() != null) {
                return tick.timestamp().toEpochMilli();
            }
        }

        // Fallback to record timestamp if event time not available
        log.warn("Event timestamp not available, using record timestamp for key: {}", record.key());
        return record.timestamp();
    }
}
