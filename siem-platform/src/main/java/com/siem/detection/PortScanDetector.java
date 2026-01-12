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
import java.util.HashSet;
import java.util.Set;

/**
 * Detects port scanning activity using windowed aggregation.
 *
 * Pattern: Count unique destination ports per source IP within a time window.
 * If unique port count exceeds threshold, generate alert.
 *
 * MITRE ATT&CK: T1046 - Network Service Scanning
 */
@Component
public class PortScanDetector {

    private static final Logger log = LoggerFactory.getLogger(PortScanDetector.class);

    private final SiemProperties properties;
    private final ObjectMapper objectMapper;

    public PortScanDetector(SiemProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @Autowired
    public void buildPipeline(StreamsBuilder streamsBuilder) {
        Serde<FirewallEvent> firewallSerde = new JsonSerde<>(FirewallEvent.class, objectMapper);
        Serde<SecurityAlert> alertSerde = new JsonSerde<>(SecurityAlert.class, objectMapper);
        Serde<PortScanAggregator> aggregatorSerde = new JsonSerde<>(PortScanAggregator.class, objectMapper);

        int windowMinutes = properties.detection().portScan().windowMinutes();
        int threshold = properties.detection().portScan().threshold();

        // Read firewall events
        KStream<String, FirewallEvent> firewallEvents = streamsBuilder
                .stream(
                        properties.kafka().topics().rawFirewallLogs(),
                        Consumed.with(Serdes.String(), firewallSerde)
                );

        // Filter for connection attempts (both allowed and blocked)
        KStream<String, FirewallEvent> connectionAttempts = firewallEvents
                .filter((key, event) ->
                        event.protocol() != null &&
                        (event.protocol().equals("TCP") || event.protocol().equals("UDP")) &&
                        event.destinationPort() > 0
                );

        // Create composite key: sourceIP -> destIP
        KStream<String, FirewallEvent> keyedBySourceDest = connectionAttempts
                .selectKey((key, event) -> event.sourceIp() + "->" + event.destinationIp());

        // Aggregate unique ports per source->dest pair in window
        KTable<Windowed<String>, PortScanAggregator> portCounts = keyedBySourceDest
                .groupByKey(Grouped.with(Serdes.String(), firewallSerde))
                .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(windowMinutes)))
                .aggregate(
                        PortScanAggregator::new,
                        (key, event, aggregator) -> aggregator.addPort(event.destinationPort()),
                        Materialized.<String, PortScanAggregator, WindowStore<Bytes, byte[]>>as("port-scan-aggregator")
                                .withKeySerde(Serdes.String())
                                .withValueSerde(aggregatorSerde)
                );

        // Detect scans exceeding threshold
        KStream<String, SecurityAlert> alerts = portCounts
                .toStream()
                .filter((windowedKey, aggregator) -> aggregator.uniquePortCount() >= threshold)
                .mapValues((windowedKey, aggregator) -> {
                    String[] parts = windowedKey.key().split("->");
                    String sourceIp = parts[0];
                    String destIp = parts.length > 1 ? parts[1] : "unknown";

                    log.warn("PORT SCAN DETECTED: {} unique ports from {} to {} in {} minutes",
                            aggregator.uniquePortCount(), sourceIp, destIp, windowMinutes);

                    return SecurityAlert.portScan(sourceIp, destIp, aggregator.uniquePortCount());
                })
                .selectKey((windowedKey, alert) -> alert.alertId());

        // Output alerts
        alerts.to(
                properties.kafka().topics().alerts(),
                Produced.with(Serdes.String(), alertSerde)
        );

        log.info("Port scan detection pipeline built: window={}min, threshold={} ports",
                windowMinutes, threshold);
    }

    /**
     * Aggregator to track unique ports scanned
     */
    public static class PortScanAggregator {
        private Set<Integer> ports = new HashSet<>();

        public PortScanAggregator() {}

        public PortScanAggregator addPort(int port) {
            ports.add(port);
            return this;
        }

        public int uniquePortCount() {
            return ports.size();
        }

        public Set<Integer> getPorts() {
            return ports;
        }

        public void setPorts(Set<Integer> ports) {
            this.ports = ports;
        }
    }
}
