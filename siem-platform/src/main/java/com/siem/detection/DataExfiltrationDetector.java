package com.siem.detection;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.siem.config.SiemProperties;
import com.siem.model.FirewallEvent;
import com.siem.model.SecurityAlert;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.state.WindowStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.support.serializer.JsonSerde;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * Detects potential data exfiltration by monitoring outbound data volume.
 *
 * Pattern: Sum outbound bytes per source IP within a time window.
 * If total exceeds threshold, generate alert.
 *
 * MITRE ATT&CK: T1041 - Exfiltration Over C2 Channel
 */
@Component
public class DataExfiltrationDetector {

    private static final Logger log = LoggerFactory.getLogger(DataExfiltrationDetector.class);

    private final SiemProperties properties;
    private final ObjectMapper objectMapper;

    public DataExfiltrationDetector(SiemProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @Autowired
    public void buildPipeline(StreamsBuilder streamsBuilder) {
        Serde<FirewallEvent> firewallSerde = new JsonSerde<>(FirewallEvent.class, objectMapper);
        Serde<SecurityAlert> alertSerde = new JsonSerde<>(SecurityAlert.class, objectMapper);
        Serde<ExfilAggregator> aggregatorSerde = new JsonSerde<>(ExfilAggregator.class, objectMapper);

        int windowMinutes = properties.detection().exfiltration().windowMinutes();
        long bytesThreshold = properties.detection().exfiltration().bytesThreshold();

        // Read firewall events
        KStream<String, FirewallEvent> firewallEvents = streamsBuilder
                .stream(
                        properties.kafka().topics().rawFirewallLogs(),
                        Consumed.with(Serdes.String(), firewallSerde)
                );

        // Filter for outbound traffic with data
        KStream<String, FirewallEvent> outboundTraffic = firewallEvents
                .filter((key, event) ->
                        "OUTBOUND".equals(event.direction()) &&
                        event.bytesOut() > 0 &&
                        event.action() == FirewallEvent.FirewallAction.ALLOW
                );

        // Group by source IP and aggregate bytes
        KTable<Windowed<String>, ExfilAggregator> bytesPerHost = outboundTraffic
                .groupBy(
                        (key, event) -> event.sourceIp(),
                        Grouped.with(Serdes.String(), firewallSerde)
                )
                .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(windowMinutes)))
                .aggregate(
                        ExfilAggregator::new,
                        (key, event, aggregator) -> aggregator.addBytes(
                                event.bytesOut(),
                                event.destinationIp()
                        ),
                        Materialized.<String, ExfilAggregator, WindowStore<Bytes, byte[]>>as("exfil-bytes-store")
                                .withKeySerde(Serdes.String())
                                .withValueSerde(aggregatorSerde)
                );

        // Detect large outbound transfers
        KStream<String, SecurityAlert> alerts = bytesPerHost
                .toStream()
                .filter((windowedKey, aggregator) -> aggregator.totalBytes() >= bytesThreshold)
                .mapValues((windowedKey, aggregator) -> {
                    String sourceIp = windowedKey.key();

                    log.warn("DATA EXFILTRATION DETECTED: {} MB outbound from {} in {} minutes",
                            aggregator.totalBytes() / (1024 * 1024), sourceIp, windowMinutes);

                    return SecurityAlert.dataExfiltration(
                            sourceIp,
                            aggregator.topDestination(),
                            aggregator.totalBytes()
                    );
                })
                .selectKey((windowedKey, alert) -> alert.alertId());

        // Output alerts
        alerts.to(
                properties.kafka().topics().alerts(),
                Produced.with(Serdes.String(), alertSerde)
        );

        log.info("Data exfiltration detection pipeline built: window={}min, threshold={} bytes",
                windowMinutes, bytesThreshold);
    }

    /**
     * Aggregator to track outbound data volume
     */
    public static class ExfilAggregator {
        private long totalBytes = 0;
        private String topDestination = "";
        private long topDestBytes = 0;

        public ExfilAggregator() {}

        public ExfilAggregator addBytes(long bytes, String destination) {
            totalBytes += bytes;
            // Track the destination receiving most data
            if (bytes > topDestBytes) {
                topDestBytes = bytes;
                topDestination = destination;
            }
            return this;
        }

        public long totalBytes() { return totalBytes; }
        public String topDestination() { return topDestination; }

        // Getters/setters for JSON serialization
        public long getTotalBytes() { return totalBytes; }
        public void setTotalBytes(long totalBytes) { this.totalBytes = totalBytes; }
        public String getTopDestination() { return topDestination; }
        public void setTopDestination(String topDestination) { this.topDestination = topDestination; }
        public long getTopDestBytes() { return topDestBytes; }
        public void setTopDestBytes(long topDestBytes) { this.topDestBytes = topDestBytes; }
    }
}
