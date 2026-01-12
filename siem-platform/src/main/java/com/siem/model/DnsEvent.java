package com.siem.model;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * DNS query/response events - useful for detecting C2, DGA, tunneling.
 */
public record DnsEvent(
    String eventId,
    Instant timestamp,
    EventSource source,
    Severity severity,
    String sourceIp,
    String destinationIp,
    String userId,
    String hostname,
    Map<String, Object> rawData,

    // DNS-specific fields
    DnsQueryType queryType,
    String queryName,         // Domain being queried
    String responseCode,      // NOERROR, NXDOMAIN, SERVFAIL
    List<String> answers,     // Resolved IPs
    long queryTimeMs,
    boolean isThreat,
    String threatCategory,    // DGA, MALWARE, PHISHING, C2
    double dgaScore,          // ML-based DGA detection score
    int queryLength,          // Long queries may indicate tunneling
    String tld                // Top-level domain
) implements SecurityEvent {

    public enum DnsQueryType {
        A,
        AAAA,
        CNAME,
        MX,
        TXT,
        NS,
        PTR,
        SOA,
        SRV
    }

    public static DnsEvent normalQuery(String srcIp, String domain, List<String> answers) {
        return new DnsEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.DNS,
            Severity.INFO,
            srcIp,
            null,
            null,
            null,
            Map.of(),
            DnsQueryType.A,
            domain,
            "NOERROR",
            answers,
            5,
            false,
            null,
            0.0,
            domain.length(),
            extractTld(domain)
        );
    }

    public static DnsEvent suspiciousDga(String srcIp, String domain, double dgaScore) {
        return new DnsEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.DNS,
            Severity.HIGH,
            srcIp,
            null,
            null,
            null,
            Map.of(),
            DnsQueryType.A,
            domain,
            "NXDOMAIN",
            List.of(),
            10,
            true,
            "DGA",
            dgaScore,
            domain.length(),
            extractTld(domain)
        );
    }

    public static DnsEvent tunnelingAttempt(String srcIp, String domain) {
        return new DnsEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.DNS,
            Severity.CRITICAL,
            srcIp,
            null,
            null,
            null,
            Map.of(),
            DnsQueryType.TXT,
            domain,
            "NOERROR",
            List.of(),
            50,
            true,
            "DNS_TUNNELING",
            0.0,
            domain.length(),
            extractTld(domain)
        );
    }

    private static String extractTld(String domain) {
        if (domain == null || !domain.contains(".")) return domain;
        String[] parts = domain.split("\\.");
        return parts[parts.length - 1];
    }
}
