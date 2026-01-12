package com.siem.detection;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.siem.config.SiemProperties;
import com.siem.model.AuthEvent;
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
 * Detects brute force attacks using windowed aggregation.
 *
 * Pattern: Count failed login attempts per source IP within a time window.
 * If count exceeds threshold, generate alert.
 *
 * MITRE ATT&CK: T1110 - Brute Force
 */
@Component
public class BruteForceDetector {

    private static final Logger log = LoggerFactory.getLogger(BruteForceDetector.class);

    private final SiemProperties properties;
    private final ObjectMapper objectMapper;

    public BruteForceDetector(SiemProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @Autowired
    public void buildPipeline(StreamsBuilder streamsBuilder) {
        Serde<AuthEvent> authEventSerde = new JsonSerde<>(AuthEvent.class, objectMapper);
        Serde<SecurityAlert> alertSerde = new JsonSerde<>(SecurityAlert.class, objectMapper);
        Serde<FailedLoginCount> countSerde = new JsonSerde<>(FailedLoginCount.class, objectMapper);

        int windowMinutes = properties.detection().bruteForce().windowMinutes();
        int threshold = properties.detection().bruteForce().threshold();

        // Read auth events
        KStream<String, AuthEvent> authEvents = streamsBuilder
                .stream(
                        properties.kafka().topics().rawAuthLogs(),
                        Consumed.with(Serdes.String(), authEventSerde)
                );

        // Filter for failed login attempts only
        KStream<String, AuthEvent> failedLogins = authEvents
                .filter((key, event) ->
                        event.action() == AuthEvent.AuthAction.LOGIN &&
                        event.status() == AuthEvent.AuthStatus.FAILURE
                );

        // Group by source IP and apply tumbling window
        KTable<Windowed<String>, Long> failedLoginCounts = failedLogins
                .groupBy(
                        (key, event) -> event.sourceIp(),  // Group by source IP
                        Grouped.with(Serdes.String(), authEventSerde)
                )
                .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(windowMinutes)))
                .count(
                        Materialized.<String, Long, WindowStore<Bytes, byte[]>>as("brute-force-counts")
                                .withKeySerde(Serdes.String())
                                .withValueSerde(Serdes.Long())
                );

        // Filter for counts exceeding threshold and generate alerts
        KStream<String, SecurityAlert> alerts = failedLoginCounts
                .toStream()
                .filter((windowedKey, count) -> count >= threshold)
                .mapValues((windowedKey, count) -> {
                    String sourceIp = windowedKey.key();
                    log.warn("BRUTE FORCE DETECTED: {} failed logins from {} in {} minutes",
                            count, sourceIp, windowMinutes);

                    return SecurityAlert.bruteForce(sourceIp, "unknown", count.intValue());
                })
                .selectKey((windowedKey, alert) -> alert.alertId());

        // Output alerts
        alerts
                .peek((key, alert) -> log.info("Generated alert: {} - {}", alert.type(), alert.title()))
                .to(
                        properties.kafka().topics().alerts(),
                        Produced.with(Serdes.String(), alertSerde)
                );

        log.info("Brute force detection pipeline built: window={}min, threshold={}",
                windowMinutes, threshold);
    }

    /**
     * Helper class for tracking failed login counts with user context
     */
    public record FailedLoginCount(
            String sourceIp,
            String targetUser,
            long count,
            long windowStart,
            long windowEnd
    ) {}
}
