package aegis

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

type staticClock struct {
	now time.Time
}

func (s staticClock) Now() time.Time {
	return s.now
}

func TestValidCapabilityIsAllowedExactlyOnce(t *testing.T) {
	authorizer, keys, policy, now := testAuthorizer(t)
	token := mustSignCapability(t, keys, policy, readClaims(policy, "read-once", now))

	result := authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token:       token,
		TraceParent: "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
	})
	if !result.Allowed || result.Decision != DecisionAllow {
		t.Fatalf("expected allow, got %+v", result)
	}
	if result.TraceID != "4bf92f3577b34da6a3ce929d0e0e4736" || result.SpanID != "00f067aa0ba902b7" {
		t.Fatalf("trace context not retained: %+v", result)
	}
	if got := result.OTelEvent.Attributes["aegis.spiffe_trust_domain"]; got != "example.org" {
		t.Fatalf("missing trust-domain attribute: %+v", result.OTelEvent.Attributes)
	}
	if result.AuditSequence != 1 || result.AuditHash == "" {
		t.Fatalf("audit record not appended: %+v", result)
	}

	replay := authorizer.Authorize(context.Background(), AuthorizationRequest{Token: token})
	if replay.Allowed || replay.Reason != "replay_detected" {
		t.Fatalf("expected replay denial, got %+v", replay)
	}
}

func TestPolicyDriftTamperExpiryAndScopeEscalationDeny(t *testing.T) {
	authorizer, keys, policy, now := testAuthorizer(t)

	stale := readClaims(policy, "stale-policy", now)
	stale.PolicyHash = "sha256:stale"
	staleToken := mustSignCapability(t, keys, policy, stale)
	result := authorizer.Authorize(context.Background(), AuthorizationRequest{Token: staleToken})
	if result.Allowed || result.Reason != "policy_hash_mismatch" {
		t.Fatalf("expected policy hash denial, got %+v", result)
	}

	escalated := readClaims(policy, "write-escalation", now)
	escalated.Action = "write"
	escalatedToken := mustSignCapability(t, keys, policy, escalated)
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{Token: escalatedToken})
	if result.Allowed || result.Reason != "policy_no_match" {
		t.Fatalf("expected policy no-match denial, got %+v", result)
	}

	expired := readClaims(policy, "expired", now)
	expired.IssuedAt = unixSeconds(now.Add(-10 * time.Minute))
	expired.ExpiresAt = unixSeconds(now.Add(-time.Minute))
	expiredToken := mustSignCapability(t, keys, policy, expired)
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{Token: expiredToken})
	if result.Allowed || result.Reason != "token_expired" {
		t.Fatalf("expected expiry denial, got %+v", result)
	}

	validForTamper := readClaims(policy, "tampered", now)
	validToken := mustSignCapability(t, keys, policy, validForTamper)
	tampered := corruptJWTPart(validToken, 1)
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{Token: tampered})
	if result.Allowed || result.Reason != "invalid_token" {
		t.Fatalf("expected tamper denial, got %+v", result)
	}
}

func TestApprovalIsSeparatelySignedAndBoundToCapability(t *testing.T) {
	authorizer, keys, policy, now := testAuthorizer(t)
	capability := deployClaims(policy, "deploy-1", now)
	token := mustSignCapability(t, keys, policy, capability)

	result := authorizer.Authorize(context.Background(), AuthorizationRequest{Token: token})
	if result.Allowed || result.Reason != "approval_required" {
		t.Fatalf("expected missing approval denial, got %+v", result)
	}

	mismatchedApproval := approvalClaims(policy, "approval-1", now, token, capability)
	mismatchedApproval.Resource = "staging/other-service"
	mismatchedToken := mustSignApproval(t, keys, mismatchedApproval)
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token:         token,
		ApprovalToken: mismatchedToken,
	})
	if result.Allowed || result.Reason != "approval_scope_mismatch" {
		t.Fatalf("expected mismatched approval denial, got %+v", result)
	}

	approval := approvalClaims(policy, "approval-2", now, token, capability)
	approvalToken := mustSignApproval(t, keys, approval)
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token:         token,
		ApprovalToken: approvalToken,
	})
	if !result.Allowed {
		t.Fatalf("expected approved capability allow, got %+v", result)
	}

	secondCapability := deployClaims(policy, "deploy-2", now)
	secondToken := mustSignCapability(t, keys, policy, secondCapability)
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token:         secondToken,
		ApprovalToken: approvalToken,
	})
	if result.Allowed || result.Reason != "approval_scope_mismatch" {
		t.Fatalf("expected approval reuse mismatch denial, got %+v", result)
	}
}

func TestRevocationKeyRotationRateLimitAndStateFailureDeny(t *testing.T) {
	authorizer, keys, policy, now := testAuthorizer(t)
	state := authorizer.State.(*MemoryStateStore)

	subjectRevoked := readClaims(policy, "subject-revoked", now)
	if err := state.RevokeSubject(context.Background(), subjectRevoked.Subject, "incident"); err != nil {
		t.Fatal(err)
	}
	token := mustSignCapability(t, keys, policy, subjectRevoked)
	result := authorizer.Authorize(context.Background(), AuthorizationRequest{Token: token})
	if result.Allowed || result.Reason != "subject_revoked" {
		t.Fatalf("expected subject revocation denial, got %+v", result)
	}

	authorizer, keys, policy, now = testAuthorizer(t)
	first := readClaims(policy, "rate-1", now)
	second := readClaims(policy, "rate-2", now)
	policy.Rules[0].RateLimit = &RateLimitSpec{Limit: 1, WindowSeconds: 60}
	authorizer.Policy = policy
	first.PolicyHash = policy.Hash()
	second.PolicyHash = policy.Hash()
	if allowed := authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token: mustSignCapability(t, keys, policy, first),
	}); !allowed.Allowed {
		t.Fatalf("expected first request below rate limit, got %+v", allowed)
	}
	limited := authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token: mustSignCapability(t, keys, policy, second),
	})
	if limited.Allowed || limited.Reason != "rate_limited" {
		t.Fatalf("expected rate limit denial, got %+v", limited)
	}

	authorizer, keys, policy, now = testAuthorizer(t)
	failedState := authorizer.State.(*MemoryStateStore)
	failedState.InjectHealthFailure(ErrStateUnavailable)
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token: mustSignCapability(t, keys, policy, readClaims(policy, "state-fails", now)),
	})
	if result.Allowed || result.Reason != "state_unavailable" {
		t.Fatalf("expected state failure denial, got %+v", result)
	}

	authorizer, keys, policy, now = testAuthorizer(t)
	failedRateState := authorizer.State.(*MemoryStateStore)
	failedRateState.InjectRateLimitFailure(ErrStateUnavailable)
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token: mustSignCapability(t, keys, policy, readClaims(policy, "rate-state-fails", now)),
	})
	if result.Allowed || result.Reason != "state_unavailable" {
		t.Fatalf("expected rate-limit state failure denial, got %+v", result)
	}

	authorizer, keys, policy, now = testAuthorizer(t)
	rotated, err := GenerateKeyRecord("next", KeyRetired, now)
	if err != nil {
		t.Fatal(err)
	}
	if err := keys.Add(rotated); err != nil {
		t.Fatal(err)
	}
	oldToken := mustSignCapability(t, keys, policy, readClaims(policy, "old-key-valid", now))
	if err := keys.RotateTo("next"); err != nil {
		t.Fatal(err)
	}
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{Token: oldToken})
	if !result.Allowed {
		t.Fatalf("expected retired key to verify until revoked, got %+v", result)
	}
	revokedClaims := readClaims(policy, "old-key-revoked", now)
	revokedToken, err := signJWT(keys.keys["primary"].Private, "primary", "capability", revokedClaims)
	if err != nil {
		t.Fatal(err)
	}
	if err := keys.Revoke("primary"); err != nil {
		t.Fatal(err)
	}
	result = authorizer.Authorize(context.Background(), AuthorizationRequest{Token: revokedToken})
	if result.Allowed || result.Reason != "revoked_signing_key" {
		t.Fatalf("expected revoked signing key denial, got %+v", result)
	}
}

func TestHTTPGatewayBoundsAndJWKS(t *testing.T) {
	authorizer, _, _, _ := testAuthorizer(t)
	handler := HTTPHandler{Authorizer: authorizer, Config: HTTPConfig{Issuer: authorizer.Policy.Issuer}}

	req := httptest.NewRequest(http.MethodPost, "/v1/authorize", strings.NewReader("{}"))
	rec := httptest.NewRecorder()
	handler.authorize(rec, req)
	if rec.Code != http.StatusUnsupportedMediaType {
		t.Fatalf("expected unsupported media type, got %d", rec.Code)
	}

	req = httptest.NewRequest(http.MethodGet, "/jwks.json", nil)
	rec = httptest.NewRecorder()
	handler.jwks(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected jwks status 200, got %d", rec.Code)
	}
	var jwks JWKS
	if err := json.Unmarshal(rec.Body.Bytes(), &jwks); err != nil {
		t.Fatal(err)
	}
	if len(jwks.Keys) != 1 || jwks.Keys[0].Alg != "EdDSA" || jwks.Keys[0].Curve != "Ed25519" {
		t.Fatalf("unexpected jwks: %+v", jwks)
	}

	req = httptest.NewRequest(http.MethodPost, "/v1/authorize", strings.NewReader("{"))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	handler.authorize(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected malformed json denial, got %d", rec.Code)
	}
}

func TestSPIFFEValidationRejectsMalformedIdentity(t *testing.T) {
	if _, err := ParseSPIFFETrustDomain("https://example.org/ns/default/sa/agent"); !errors.Is(err, ErrInvalidIdentity) {
		t.Fatalf("expected non-SPIFFE identity rejection, got %v", err)
	}
	if _, err := ParseSPIFFETrustDomain("spiffe://example.org/ns/../sa/agent"); !errors.Is(err, ErrInvalidIdentity) {
		t.Fatalf("expected traversal identity rejection, got %v", err)
	}
}

func TestMissingAuditSinkDeniesWithoutPanic(t *testing.T) {
	authorizer, keys, policy, now := testAuthorizer(t)
	authorizer.Audit = nil
	result := authorizer.Authorize(context.Background(), AuthorizationRequest{
		Token: mustSignCapability(t, keys, policy, readClaims(policy, "missing-audit", now)),
	})
	if result.Allowed || result.Reason != "audit_unavailable" {
		t.Fatalf("expected audit-unavailable denial, got %+v", result)
	}
}

func BenchmarkPolicyEvaluation(b *testing.B) {
	policy := testPolicy()
	identity, err := WorkloadIdentityFromClaims(readClaims(policy, "bench", time.Now().UTC()))
	if err != nil {
		b.Fatal(err)
	}
	scope := Scope{Tool: "mcp.billing", Action: "read", Resource: "invoices/2026-09"}
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		decision := policy.Evaluate(identity, scope)
		if decision.Decision != DecisionAllow {
			b.Fatalf("unexpected decision: %+v", decision)
		}
	}
}

func testAuthorizer(t *testing.T) (*Authorizer, *KeySet, Policy, time.Time) {
	t.Helper()
	now := time.Date(2026, 9, 5, 12, 0, 0, 0, time.UTC)
	primary, err := GenerateKeyRecord("primary", KeyActive, now)
	if err != nil {
		t.Fatal(err)
	}
	keys, err := NewKeySet(primary)
	if err != nil {
		t.Fatal(err)
	}
	policy := testPolicy()
	state := NewMemoryStateStore()
	state.SetClock(staticClock{now: now})
	authorizer := NewAuthorizer(policy, keys, state, NewMemoryAuditLog())
	authorizer.Clock = staticClock{now: now}
	return authorizer, keys, policy, now
}

func testPolicy() Policy {
	return Policy{
		Version:              "aegis.policy.v1",
		Issuer:               "https://issuer.example",
		Audience:             "aegis-authorizer",
		DefaultMaxTTLSeconds: 300,
		Rules: []Rule{
			{
				ID:                 "allow-finance-read",
				Effect:             "allow",
				Subjects:           []string{"spiffe://example.org/ns/finance/sa/sentinel-agent"},
				SPIFFETrustDomains: []string{"example.org"},
				Tools:              []string{"mcp.billing"},
				Actions:            []string{"read"},
				Resources:          []string{"invoices/*"},
				MaxTTLSeconds:      120,
				RateLimit:          &RateLimitSpec{Limit: 4, WindowSeconds: 60},
			},
			{
				ID:                 "allow-approved-deploy",
				Effect:             "allow",
				Subjects:           []string{"spiffe://example.org/ns/platform/sa/release-agent"},
				SPIFFETrustDomains: []string{"example.org"},
				Tools:              []string{"mcp.deploy"},
				Actions:            []string{"promote"},
				Resources:          []string{"staging/*"},
				RequireApproval:    true,
				MaxTTLSeconds:      60,
			},
		},
	}
}

func readClaims(policy Policy, jti string, now time.Time) CapabilityClaims {
	return CapabilityClaims{
		Issuer:     policy.Issuer,
		Subject:    "spiffe://example.org/ns/finance/sa/sentinel-agent",
		Audience:   Audience{policy.Audience},
		ExpiresAt:  unixSeconds(now.Add(time.Minute)),
		IssuedAt:   unixSeconds(now),
		JTI:        jti,
		Tool:       "mcp.billing",
		Action:     "read",
		Resource:   "invoices/2026-09",
		PolicyHash: policy.Hash(),
		SPIFFEID:   "spiffe://example.org/ns/finance/sa/sentinel-agent",
	}
}

func deployClaims(policy Policy, jti string, now time.Time) CapabilityClaims {
	return CapabilityClaims{
		Issuer:     policy.Issuer,
		Subject:    "spiffe://example.org/ns/platform/sa/release-agent",
		Audience:   Audience{policy.Audience},
		ExpiresAt:  unixSeconds(now.Add(45 * time.Second)),
		IssuedAt:   unixSeconds(now),
		JTI:        jti,
		Tool:       "mcp.deploy",
		Action:     "promote",
		Resource:   "staging/api",
		PolicyHash: policy.Hash(),
		SPIFFEID:   "spiffe://example.org/ns/platform/sa/release-agent",
	}
}

func approvalClaims(policy Policy, jti string, now time.Time, token string, capability CapabilityClaims) ApprovalClaims {
	return ApprovalClaims{
		Issuer:           policy.Issuer,
		Subject:          capability.Subject,
		Audience:         Audience{policy.Audience},
		ExpiresAt:        unixSeconds(now.Add(45 * time.Second)),
		IssuedAt:         unixSeconds(now),
		JTI:              jti,
		CapabilityJTI:    capability.JTI,
		CapabilitySHA256: tokenHash(token),
		Tool:             capability.Tool,
		Action:           capability.Action,
		Resource:         capability.Resource,
		PolicyHash:       capability.PolicyHash,
		ApprovedBy:       "human:change-manager",
	}
}

func mustSignCapability(t *testing.T, keys *KeySet, policy Policy, claims CapabilityClaims) string {
	t.Helper()
	token, err := SignCapability(keys, claims)
	if err != nil {
		t.Fatal(err)
	}
	return token
}

func mustSignApproval(t *testing.T, keys *KeySet, claims ApprovalClaims) string {
	t.Helper()
	token, err := SignApproval(keys, claims)
	if err != nil {
		t.Fatal(err)
	}
	return token
}

func corruptJWTPart(token string, part int) string {
	parts := strings.Split(token, ".")
	replacement := byte('A')
	if parts[part][0] == replacement {
		replacement = 'B'
	}
	parts[part] = string(replacement) + parts[part][1:]
	return strings.Join(parts, ".")
}