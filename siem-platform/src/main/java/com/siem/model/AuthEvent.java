package com.siem.model;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Authentication/Identity events from IAM systems, AD, SSO, etc.
 */
public record AuthEvent(
    String eventId,
    Instant timestamp,
    EventSource source,
    Severity severity,
    String sourceIp,
    String destinationIp,
    String userId,
    String hostname,
    Map<String, Object> rawData,

    // Auth-specific fields
    AuthAction action,
    AuthStatus status,
    String authMethod,        // password, mfa, sso, api_key
    String application,       // Target application
    String userAgent,
    String geoLocation,
    String sessionId,
    int failedAttempts,       // For tracking brute force
    String failureReason
) implements SecurityEvent {

    public enum AuthAction {
        LOGIN,
        LOGOUT,
        PASSWORD_CHANGE,
        MFA_CHALLENGE,
        MFA_SUCCESS,
        MFA_FAILURE,
        PRIVILEGE_ESCALATION,
        ACCOUNT_LOCKOUT,
        ACCOUNT_UNLOCK,
        API_KEY_USED,
        TOKEN_REFRESH
    }

    public enum AuthStatus {
        SUCCESS,
        FAILURE,
        BLOCKED,
        CHALLENGED
    }

    public static AuthEvent loginSuccess(String userId, String sourceIp, String application) {
        return new AuthEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.AUTH,
            Severity.INFO,
            sourceIp,
            null,
            userId,
            null,
            Map.of(),
            AuthAction.LOGIN,
            AuthStatus.SUCCESS,
            "password",
            application,
            null,
            null,
            null,
            0,
            null
        );
    }

    public static AuthEvent loginFailure(String userId, String sourceIp, String reason) {
        return new AuthEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.AUTH,
            Severity.MEDIUM,
            sourceIp,
            null,
            userId,
            null,
            Map.of(),
            AuthAction.LOGIN,
            AuthStatus.FAILURE,
            "password",
            null,
            null,
            null,
            null,
            0,
            reason
        );
    }

    public static AuthEvent privilegeEscalation(String userId, String sourceIp) {
        return new AuthEvent(
            UUID.randomUUID().toString(),
            Instant.now(),
            EventSource.AUTH,
            Severity.HIGH,
            sourceIp,
            null,
            userId,
            null,
            Map.of(),
            AuthAction.PRIVILEGE_ESCALATION,
            AuthStatus.SUCCESS,
            null,
            null,
            null,
            null,
            null,
            0,
            null
        );
    }
}
