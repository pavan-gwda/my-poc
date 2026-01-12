package com.siem.model;

import java.time.Instant;
import java.util.Map;

/**
 * Base interface for all security events.
 * Provides common fields needed for correlation and analysis.
 */
public interface SecurityEvent {

    String eventId();
    Instant timestamp();
    EventSource source();
    Severity severity();
    String sourceIp();
    String destinationIp();
    String userId();
    String hostname();
    Map<String, Object> rawData();

    enum EventSource {
        AUTH,
        FIREWALL,
        WEB,
        DNS,
        ENDPOINT,
        NETWORK,
        CLOUD
    }

    enum Severity {
        CRITICAL(1),
        HIGH(2),
        MEDIUM(3),
        LOW(4),
        INFO(5);

        private final int level;

        Severity(int level) {
            this.level = level;
        }

        public int getLevel() {
            return level;
        }

        public boolean isHigherThan(Severity other) {
            return this.level < other.level;
        }
    }
}
