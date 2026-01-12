package com.siem.model;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Network firewall events - traffic logs, blocked connections, IDS alerts.
 */
public record FirewallEvent(
    String eventId,
    Instant timestamp,
    EventSource source,
    Severity severity,
    String sourceIp,
    String destinationIp,
    String userId,
    String hostname,
    Map<String, Object> rawData,

    // Firewall-specific fields
    FirewallAction action,
    String protocol,          // TCP, UDP, ICMP
    int sourcePort,
    int destinationPort,
    long bytesIn,
    long bytesOut,
    long packetsIn,
    long packetsOut,
    String direction,         // INBOUND, OUTBOUND
    String rule,              // Firewall rule that matched
    String zone,              // DMZ, INTERNAL, EXTERNAL
    String threatName,        // If IDS detected something
    String category           // MALWARE, BOTNET, SCAN, etc.
) implements SecurityEvent {

    public enum FirewallAction {
        ALLOW,
        DENY,
        DROP,
        REJECT,
        ALERT,
        LOG
    }

    public static FirewallEvent blocked(String srcIp, String dstIp, int dstPort, String reason) {
        return new FirewallEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.FIREWALL,
            Severity.MEDIUM,
            srcIp,
            dstIp,
            null,
            null,
            Map.of(),
            FirewallAction.DENY,
            "TCP",
            0,
            dstPort,
            0,
            0,
            0,
            0,
            "INBOUND",
            reason,
            "EXTERNAL",
            null,
            null
        );
    }

    public static FirewallEvent portScan(String srcIp, String dstIp, int port) {
        return new FirewallEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.FIREWALL,
            Severity.HIGH,
            srcIp,
            dstIp,
            null,
            null,
            Map.of(),
            FirewallAction.ALERT,
            "TCP",
            0,
            port,
            0,
            0,
            1,
            0,
            "INBOUND",
            "PORT_SCAN_DETECTED",
            "EXTERNAL",
            "Port Scan",
            "SCAN"
        );
    }

    public static FirewallEvent largeOutbound(String srcIp, String dstIp, long bytes) {
        return new FirewallEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.FIREWALL,
            Severity.MEDIUM,
            srcIp,
            dstIp,
            null,
            null,
            Map.of(),
            FirewallAction.ALLOW,
            "TCP",
            0,
            443,
            0,
            bytes,
            0,
            0,
            "OUTBOUND",
            null,
            "INTERNAL",
            null,
            null
        );
    }
}
