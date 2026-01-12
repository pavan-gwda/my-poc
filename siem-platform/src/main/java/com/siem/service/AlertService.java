package com.siem.service;

import com.siem.model.SecurityAlert;
import com.siem.model.SecurityEvent;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.stream.Collectors;

/**
 * Service for managing and querying security alerts.
 *
 * In production, this would be backed by a database (Elasticsearch, TimescaleDB).
 * For learning purposes, uses in-memory storage with TTL.
 */
@Service
public class AlertService {

    private static final int MAX_ALERTS = 10000;
    private static final int RETENTION_HOURS = 24;

    private final Deque<SecurityAlert> recentAlerts = new ConcurrentLinkedDeque<>();
    private final Map<String, SecurityAlert> alertsById = new ConcurrentHashMap<>();
    private final Map<SecurityEvent.Severity, Long> severityCounts = new ConcurrentHashMap<>();

    /**
     * Store a new alert
     */
    public void storeAlert(SecurityAlert alert) {
        // Maintain max size
        while (recentAlerts.size() >= MAX_ALERTS) {
            SecurityAlert removed = recentAlerts.pollLast();
            if (removed != null) {
                alertsById.remove(removed.alertId());
            }
        }

        recentAlerts.addFirst(alert);
        alertsById.put(alert.alertId(), alert);

        // Update counts
        severityCounts.merge(alert.severity(), 1L, Long::sum);
    }

    /**
     * Get alert by ID
     */
    public Optional<SecurityAlert> getAlert(String alertId) {
        return Optional.ofNullable(alertsById.get(alertId));
    }

    /**
     * Get recent alerts with optional filters
     */
    public List<SecurityAlert> getRecentAlerts(
            SecurityEvent.Severity minSeverity,
            SecurityAlert.AlertType type,
            String sourceIp,
            int limit) {

        return recentAlerts.stream()
                .filter(alert -> minSeverity == null || alert.severity().ordinal() <= minSeverity.ordinal())
                .filter(alert -> type == null || alert.type() == type)
                .filter(alert -> sourceIp == null || sourceIp.equals(alert.sourceIp()))
                .limit(limit > 0 ? limit : 100)
                .collect(Collectors.toList());
    }

    /**
     * Get alerts from the last N hours
     */
    public List<SecurityAlert> getAlertsInTimeRange(int hours) {
        Instant cutoff = Instant.now().minus(hours, ChronoUnit.HOURS);

        return recentAlerts.stream()
                .filter(alert -> alert.timestamp().isAfter(cutoff))
                .collect(Collectors.toList());
    }

    /**
     * Get alert counts by severity
     */
    public Map<SecurityEvent.Severity, Long> getAlertCountsBySeverity() {
        return new EnumMap<>(severityCounts);
    }

    /**
     * Get alert counts by type for the last N hours
     */
    public Map<SecurityAlert.AlertType, Long> getAlertCountsByType(int hours) {
        Instant cutoff = Instant.now().minus(hours, ChronoUnit.HOURS);

        return recentAlerts.stream()
                .filter(alert -> alert.timestamp().isAfter(cutoff))
                .collect(Collectors.groupingBy(
                        SecurityAlert::type,
                        () -> new EnumMap<>(SecurityAlert.AlertType.class),
                        Collectors.counting()
                ));
    }

    /**
     * Get top source IPs by alert count
     */
    public Map<String, Long> getTopSourceIps(int hours, int limit) {
        Instant cutoff = Instant.now().minus(hours, ChronoUnit.HOURS);

        return recentAlerts.stream()
                .filter(alert -> alert.timestamp().isAfter(cutoff))
                .filter(alert -> alert.sourceIp() != null)
                .collect(Collectors.groupingBy(
                        SecurityAlert::sourceIp,
                        Collectors.counting()
                ))
                .entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(limit)
                .collect(Collectors.toMap(
                        Map.Entry::getKey,
                        Map.Entry::getValue,
                        (a, b) -> a,
                        LinkedHashMap::new
                ));
    }

    /**
     * Get dashboard summary
     */
    public DashboardSummary getDashboardSummary() {
        List<SecurityAlert> last24h = getAlertsInTimeRange(24);
        List<SecurityAlert> lastHour = getAlertsInTimeRange(1);

        long criticalCount = last24h.stream()
                .filter(a -> a.severity() == SecurityEvent.Severity.CRITICAL)
                .count();
        long highCount = last24h.stream()
                .filter(a -> a.severity() == SecurityEvent.Severity.HIGH)
                .count();

        return new DashboardSummary(
                last24h.size(),
                lastHour.size(),
                criticalCount,
                highCount,
                getAlertCountsByType(24),
                getTopSourceIps(24, 10)
        );
    }

    /**
     * Dashboard summary DTO
     */
    public record DashboardSummary(
            long totalAlerts24h,
            long alertsLastHour,
            long criticalAlerts,
            long highAlerts,
            Map<SecurityAlert.AlertType, Long> alertsByType,
            Map<String, Long> topSourceIps
    ) {}
}
