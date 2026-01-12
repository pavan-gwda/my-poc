package com.siem.api;

import com.siem.model.SecurityAlert;
import com.siem.model.SecurityEvent;
import com.siem.service.AlertService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for security alerts and dashboard data.
 */
@RestController
@RequestMapping("/api/alerts")
@CrossOrigin(origins = "*")
public class AlertController {

    private static final Logger log = LoggerFactory.getLogger(AlertController.class);

    private final AlertService alertService;

    public AlertController(AlertService alertService) {
        this.alertService = alertService;
    }

    /**
     * Get dashboard summary
     */
    @GetMapping("/dashboard")
    public ResponseEntity<AlertService.DashboardSummary> getDashboard() {
        return ResponseEntity.ok(alertService.getDashboardSummary());
    }

    /**
     * Get recent alerts with optional filters
     */
    @GetMapping
    public ResponseEntity<List<SecurityAlert>> getAlerts(
            @RequestParam(required = false) SecurityEvent.Severity minSeverity,
            @RequestParam(required = false) SecurityAlert.AlertType type,
            @RequestParam(required = false) String sourceIp,
            @RequestParam(defaultValue = "100") int limit) {

        List<SecurityAlert> alerts = alertService.getRecentAlerts(minSeverity, type, sourceIp, limit);
        return ResponseEntity.ok(alerts);
    }

    /**
     * Get alert by ID
     */
    @GetMapping("/{alertId}")
    public ResponseEntity<SecurityAlert> getAlert(@PathVariable String alertId) {
        return alertService.getAlert(alertId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Get alerts in time range
     */
    @GetMapping("/timerange")
    public ResponseEntity<List<SecurityAlert>> getAlertsInTimeRange(
            @RequestParam(defaultValue = "24") int hours) {

        List<SecurityAlert> alerts = alertService.getAlertsInTimeRange(hours);
        return ResponseEntity.ok(alerts);
    }

    /**
     * Get alert counts by severity
     */
    @GetMapping("/stats/severity")
    public ResponseEntity<Map<SecurityEvent.Severity, Long>> getAlertsBySeverity() {
        return ResponseEntity.ok(alertService.getAlertCountsBySeverity());
    }

    /**
     * Get alert counts by type
     */
    @GetMapping("/stats/type")
    public ResponseEntity<Map<SecurityAlert.AlertType, Long>> getAlertsByType(
            @RequestParam(defaultValue = "24") int hours) {

        return ResponseEntity.ok(alertService.getAlertCountsByType(hours));
    }

    /**
     * Get top source IPs
     */
    @GetMapping("/stats/top-sources")
    public ResponseEntity<Map<String, Long>> getTopSourceIps(
            @RequestParam(defaultValue = "24") int hours,
            @RequestParam(defaultValue = "10") int limit) {

        return ResponseEntity.ok(alertService.getTopSourceIps(hours, limit));
    }
}
