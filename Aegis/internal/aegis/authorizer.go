package aegis

import (
	"context"
	"errors"
	"time"
)

type AuthorizationRequest struct {
	Token         string `json:"token"`
	ApprovalToken string `json:"approval_token,omitempty"`
	TraceParent   string `json:"-"`
}

type AuthorizationResult struct {
	Decision      string    `json:"decision"`
	Allowed       bool      `json:"allowed"`
	Reason        string    `json:"reason"`
	Subject       string    `json:"subject,omitempty"`
	SPIFFEID      string    `json:"spiffe_id,omitempty"`
	TrustDomain   string    `json:"trust_domain,omitempty"`
	Tool          string    `json:"tool,omitempty"`
	Action        string    `json:"action,omitempty"`
	Resource      string    `json:"resource,omitempty"`
	RuleID        string    `json:"rule_id,omitempty"`
	PolicyHash    string    `json:"policy_hash,omitempty"`
	SigningKeyID  string    `json:"signing_key_id,omitempty"`
	TraceID       string    `json:"trace_id"`
	SpanID        string    `json:"span_id"`
	AuditSequence int64     `json:"audit_sequence,omitempty"`
	AuditHash     string    `json:"audit_hash,omitempty"`
	ObservedAt    time.Time `json:"-"`
	OTelEvent     OTelEvent `json:"otel_event"`
}

type Authorizer struct {
	Policy      Policy
	Keys        *KeySet
	State       StateStore
	Audit       AuditSink
	Clock       Clock
}

func NewAuthorizer(policy Policy, keys *KeySet, state StateStore, audit AuditSink) *Authorizer {
	return &Authorizer{
		Policy: policy,
		Keys:   keys,
		State:  state,
		Audit:  audit,
		Clock:  RealClock{},
	}
}

func (a *Authorizer) Authorize(ctx context.Context, request AuthorizationRequest) AuthorizationResult {
	clock := a.Clock
	if clock == nil {
		clock = RealClock{}
	}
	now := clock.Now().UTC()
	traceContext := TraceContextFromParent(request.TraceParent)
	result := AuthorizationResult{
		Decision:   DecisionDeny,
		Allowed:    false,
		Reason:     "internal_error",
		TraceID:    traceContext.TraceID,
		SpanID:     traceContext.SpanID,
		ObservedAt: now,
		PolicyHash: a.Policy.Hash(),
	}
	deny := func(reason string) AuthorizationResult {
		result.Decision = DecisionDeny
		result.Allowed = false
		result.Reason = reason
		return a.finish(ctx, result)
	}
	if a.Keys == nil || a.State == nil || a.Audit == nil {
		return deny("configuration_unavailable")
	}
	if err := a.State.Health(ctx); err != nil {
		return deny("state_unavailable")
	}
	verified, err := a.Keys.VerifyCapability(request.Token, now)
	if err != nil {
		return deny(reasonForTokenError(err))
	}
	claims := verified.Claims
	result.SigningKeyID = verified.SigningKey
	result.Subject = claims.Subject
	result.Tool = claims.Tool
	result.Action = claims.Action
	result.Resource = claims.Resource
	if err := claims.Validate(now, a.Policy.Issuer, a.Policy.Audience); err != nil {
		return deny(reasonForTokenError(err))
	}
	identity, err := WorkloadIdentityFromClaims(claims)
	if err != nil {
		return deny("invalid_workload_identity")
	}
	result.SPIFFEID = identity.SPIFFEID
	result.TrustDomain = identity.TrustDomain
	revoked, err := a.State.IsSubjectRevoked(ctx, identity.Subject)
	if err != nil {
		return deny("state_unavailable")
	}
	if revoked {
		return deny("subject_revoked")
	}
	if claims.PolicyHash != a.Policy.Hash() {
		return deny("policy_hash_mismatch")
	}
	policyDecision := a.Policy.Evaluate(identity, claims.Scope())
	result.RuleID = policyDecision.Rule.ID
	if policyDecision.Decision != DecisionAllow {
		return deny(policyDecision.Reason)
	}
	if exceedsTTL(claims, policyDecision.Rule, a.Policy) {
		return deny("capability_ttl_exceeds_policy")
	}
	if policyDecision.Rule.RequireApproval {
		if err := a.verifyApproval(ctx, request.ApprovalToken, verified, policyDecision.Rule, now); err != nil {
			return deny(err.Error())
		}
	}
	if policyDecision.Rule.RateLimit != nil {
		key := identity.Subject + "|" + claims.Tool + "|" + claims.Action
		if err := a.State.ReserveRateLimit(ctx, key, *policyDecision.Rule.RateLimit, now); err != nil {
			return deny(reasonForStateError(err))
		}
	}
	if err := a.State.ReserveJTI(ctx, claims.JTI, time.Unix(claims.ExpiresAt, 0)); err != nil {
		return deny(reasonForStateError(err))
	}
	result.Decision = DecisionAllow
	result.Allowed = true
	result.Reason = "authorized"
	return a.finish(ctx, result)
}

func (a *Authorizer) verifyApproval(
	ctx context.Context,
	approvalToken string,
	capability VerifiedCapability,
	rule Rule,
	now time.Time,
) error {
	if approvalToken == "" {
		return errors.New("approval_required")
	}
	verifiedApproval, err := a.Keys.VerifyApproval(approvalToken, now)
	if err != nil {
		return errors.New(reasonForTokenError(err))
	}
	claims := verifiedApproval.Claims
	if err := claims.Validate(now, a.Policy.Issuer, a.Policy.Audience); err != nil {
		return errors.New(reasonForTokenError(err))
	}
	capabilityClaims := capability.Claims
	if claims.CapabilityJTI != capabilityClaims.JTI ||
		claims.CapabilitySHA256 != capability.TokenHash ||
		claims.Tool != capabilityClaims.Tool ||
		claims.Action != capabilityClaims.Action ||
		claims.Resource != capabilityClaims.Resource ||
		claims.PolicyHash != capabilityClaims.PolicyHash ||
		claims.Subject != capabilityClaims.Subject {
		return errors.New("approval_scope_mismatch")
	}
	if !rule.RequireApproval {
		return nil
	}
	if err := a.State.ReserveJTI(ctx, claims.JTI, time.Unix(claims.ExpiresAt, 0)); err != nil {
		return errors.New(reasonForStateError(err))
	}
	return nil
}

func (a *Authorizer) finish(ctx context.Context, result AuthorizationResult) AuthorizationResult {
	result.OTelEvent = NewOTelEvent(result)
	if a.Audit == nil {
		result.Decision = DecisionDeny
		result.Allowed = false
		result.Reason = "audit_unavailable"
		result.OTelEvent = NewOTelEvent(result)
		return result
	}
	sequence, hash, err := a.Audit.Append(ctx, result)
	if err != nil {
		result.Decision = DecisionDeny
		result.Allowed = false
		result.Reason = "audit_unavailable"
		result.OTelEvent = NewOTelEvent(result)
		return result
	}
	result.AuditSequence = sequence
	result.AuditHash = hash
	return result
}

func exceedsTTL(claims CapabilityClaims, rule Rule, policy Policy) bool {
	maxTTL := rule.MaxTTLSeconds
	if maxTTL <= 0 {
		maxTTL = policy.DefaultMaxTTLSeconds
	}
	if maxTTL <= 0 {
		return false
	}
	return claims.ExpiresAt-claims.IssuedAt > int64(maxTTL)
}

func reasonForTokenError(err error) string {
	switch {
	case errors.Is(err, ErrExpiredToken):
		return "token_expired"
	case errors.Is(err, ErrNotYetValid):
		return "token_not_yet_valid"
	case errors.Is(err, ErrUnknownKey):
		return "unknown_signing_key"
	case errors.Is(err, ErrRevokedKey):
		return "revoked_signing_key"
	default:
		return "invalid_token"
	}
}

func reasonForStateError(err error) string {
	switch {
	case errors.Is(err, ErrReplay):
		return "replay_detected"
	case errors.Is(err, ErrRevoked):
		return "capability_revoked"
	case errors.Is(err, ErrRateLimited):
		return "rate_limited"
	default:
		return "state_unavailable"
	}
}
