package com.siem.simulator;

import com.siem.config.SiemProperties;
import com.siem.model.AuthEvent;
import com.siem.model.DnsEvent;
import com.siem.model.FirewallEvent;
import com.siem.model.SecurityEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Simulates realistic security log events for testing.
 *
 * Generates:
 * - Normal traffic patterns
 * - Periodic attack simulations (brute force, port scans, data exfiltration, DGA)
 */
@Component
@ConditionalOnProperty(name = "siem.simulator.enabled", havingValue = "true", matchIfMissing = true)
public class LogSimulator {

    private static final Logger log = LoggerFactory.getLogger(LogSimulator.class);

    private final KafkaTemplate<String, AuthEvent> authTemplate;
    private final KafkaTemplate<String, FirewallEvent> firewallTemplate;
    private final KafkaTemplate<String, DnsEvent> dnsTemplate;
    private final SiemProperties properties;

    // Simulated infrastructure
    private static final List<String> INTERNAL_IPS = List.of(
            "10.0.1.10", "10.0.1.11", "10.0.1.12", "10.0.1.20", "10.0.1.21",
            "10.0.2.10", "10.0.2.11", "10.0.2.12", "10.0.3.100", "10.0.3.101"
    );

    private static final List<String> EXTERNAL_IPS = List.of(
            "203.0.113.50", "198.51.100.25", "192.0.2.100", "45.33.32.156",
            "8.8.8.8", "1.1.1.1", "208.67.222.222"
    );

    private static final List<String> USERNAMES = List.of(
            "jsmith", "agarcia", "mwilson", "ljohnson", "klee",
            "admin", "root", "service_account", "backup_user"
    );

    private static final List<String> LEGITIMATE_DOMAINS = List.of(
            "google.com", "github.com", "stackoverflow.com", "aws.amazon.com",
            "office365.com", "slack.com", "zoom.us", "salesforce.com"
    );

    private final Random random = new Random();
    private int eventCounter = 0;

    public LogSimulator(
            @Qualifier("authKafkaTemplate") KafkaTemplate<String, AuthEvent> authTemplate,
            @Qualifier("firewallKafkaTemplate") KafkaTemplate<String, FirewallEvent> firewallTemplate,
            @Qualifier("dnsKafkaTemplate") KafkaTemplate<String, DnsEvent> dnsTemplate,
            SiemProperties properties) {
        this.authTemplate = authTemplate;
        this.firewallTemplate = firewallTemplate;
        this.dnsTemplate = dnsTemplate;
        this.properties = properties;
        log.info("Log simulator initialized");
    }

    /**
     * Generate normal traffic every second
     */
    @Scheduled(fixedRate = 1000)
    public void generateNormalTraffic() {
        // Mix of auth, firewall, and DNS events
        generateAuthEvent(false);
        generateFirewallEvent(false);
        generateDnsEvent(false);

        eventCounter += 3;
        if (eventCounter % 100 == 0) {
            log.info("Generated {} events", eventCounter);
        }
    }

    /**
     * Simulate brute force attack periodically
     */
    @Scheduled(fixedRate = 60000, initialDelay = 30000)
    public void simulateBruteForceAttack() {
        if (random.nextDouble() > 0.3) return; // 30% chance

        String attackerIp = randomExternal();
        String targetUser = randomFrom(USERNAMES);

        log.warn("SIMULATING brute force attack from {} against user {}", attackerIp, targetUser);

        // Generate 15 failed login attempts rapidly
        for (int i = 0; i < 15; i++) {
            AuthEvent event = AuthEvent.loginFailure(targetUser, attackerIp, "INVALID_PASSWORD");
            authTemplate.send(properties.kafka().topics().rawAuthLogs(), attackerIp, event);
        }
    }

    /**
     * Simulate port scan periodically
     */
    @Scheduled(fixedRate = 90000, initialDelay = 45000)
    public void simulatePortScan() {
        if (random.nextDouble() > 0.25) return; // 25% chance

        String attackerIp = randomExternal();
        String targetIp = randomInternal();

        log.warn("SIMULATING port scan from {} to {}", attackerIp, targetIp);

        // Scan 30 different ports
        List<Integer> ports = Arrays.asList(21, 22, 23, 25, 53, 80, 110, 135, 139, 143,
                443, 445, 993, 995, 1433, 1521, 3306, 3389, 5432, 5900,
                6379, 8080, 8443, 9000, 9200, 27017, 27018, 28017, 50000, 50001);

        for (int port : ports) {
            FirewallEvent event = FirewallEvent.portScan(attackerIp, targetIp, port);
            firewallTemplate.send(properties.kafka().topics().rawFirewallLogs(), attackerIp, event);
        }
    }

    /**
     * Simulate data exfiltration periodically
     */
    @Scheduled(fixedRate = 120000, initialDelay = 60000)
    public void simulateDataExfiltration() {
        if (random.nextDouble() > 0.2) return; // 20% chance

        String compromisedHost = randomInternal();
        String exfilDestination = randomExternal();

        log.warn("SIMULATING data exfiltration from {} to {}", compromisedHost, exfilDestination);

        // Large outbound transfers
        for (int i = 0; i < 10; i++) {
            long bytesOut = ThreadLocalRandom.current().nextLong(50_000_000, 200_000_000); // 50-200 MB
            FirewallEvent event = FirewallEvent.largeOutbound(compromisedHost, exfilDestination, bytesOut);
            firewallTemplate.send(properties.kafka().topics().rawFirewallLogs(), compromisedHost, event);
        }
    }

    /**
     * Simulate DGA malware periodically
     */
    @Scheduled(fixedRate = 45000, initialDelay = 20000)
    public void simulateDgaMalware() {
        if (random.nextDouble() > 0.35) return; // 35% chance

        String infectedHost = randomInternal();

        log.warn("SIMULATING DGA malware from {}", infectedHost);

        // Generate algorithmically-generated domains
        for (int i = 0; i < 20; i++) {
            String dgaDomain = generateDgaDomain();
            double dgaScore = 0.7 + random.nextDouble() * 0.3; // Score between 0.7 and 1.0
            DnsEvent event = DnsEvent.suspiciousDga(infectedHost, dgaDomain, dgaScore);
            dnsTemplate.send(properties.kafka().topics().rawDnsLogs(), infectedHost, event);
        }
    }

    // ==================== NORMAL EVENT GENERATORS ====================

    private void generateAuthEvent(boolean isAttack) {
        String sourceIp = isAttack ? randomExternal() : randomInternal();
        String username = randomFrom(USERNAMES);
        boolean success = !isAttack && random.nextDouble() > 0.05; // 95% success for normal

        AuthEvent event;
        if (success) {
            event = AuthEvent.loginSuccess(username, sourceIp, "internal-app");
        } else {
            event = AuthEvent.loginFailure(username, sourceIp, "INVALID_PASSWORD");
        }

        authTemplate.send(properties.kafka().topics().rawAuthLogs(), sourceIp, event);
    }

    private void generateFirewallEvent(boolean isAttack) {
        String sourceIp = random.nextBoolean() ? randomInternal() : randomExternal();
        String destIp = sourceIp.startsWith("10.") ? randomExternal() : randomInternal();
        boolean isBlocked = random.nextDouble() < 0.1; // 10% blocked

        FirewallEvent event;
        if (sourceIp.startsWith("10.")) {
            // Outbound traffic
            long bytes = ThreadLocalRandom.current().nextLong(1000, 100000);
            event = FirewallEvent.largeOutbound(sourceIp, destIp, bytes);
        } else {
            // Inbound traffic
            int port = randomFrom(List.of(80, 443, 22, 3306, 5432, 8080));
            event = FirewallEvent.blocked(sourceIp, destIp, port, isBlocked ? "POLICY_DENY" : "ALLOWED");
        }

        firewallTemplate.send(properties.kafka().topics().rawFirewallLogs(), sourceIp, event);
    }

    private void generateDnsEvent(boolean isMalicious) {
        String sourceIp = randomInternal();
        String domain = randomFrom(LEGITIMATE_DOMAINS);

        DnsEvent event = DnsEvent.normalQuery(sourceIp, domain, List.of(randomExternal()));
        dnsTemplate.send(properties.kafka().topics().rawDnsLogs(), sourceIp, event);
    }

    // ==================== HELPERS ====================

    private String generateDgaDomain() {
        // Generate random-looking domain typical of DGA
        int length = ThreadLocalRandom.current().nextInt(12, 25);
        StringBuilder sb = new StringBuilder();
        String chars = "abcdefghijklmnopqrstuvwxyz0123456789";

        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }

        String[] tlds = {"xyz", "top", "club", "work", "bid"};
        sb.append(".").append(tlds[random.nextInt(tlds.length)]);

        return sb.toString();
    }

    private String randomInternal() {
        return randomFrom(INTERNAL_IPS);
    }

    private String randomExternal() {
        return randomFrom(EXTERNAL_IPS);
    }

    private <T> T randomFrom(List<T> list) {
        return list.get(random.nextInt(list.size()));
    }
}
