package aegis

import (
	"crypto/rand"
	"encoding/hex"
	"strings"
	"time"
)

type TraceContext struct {
	TraceID string
	SpanID  string
}

func TraceContextFromParent(traceparent string) TraceContext {
	parts := strings.Split(traceparent, "-")
	if len(parts) == 4 && len(parts[1]) == 32 && len(parts[2]) == 16 {
		if _, err := hex.DecodeString(parts[1]); err == nil {
			if _, err := hex.DecodeString(parts[2]); err == nil {
				return TraceContext{TraceID: parts[1], SpanID: parts[2]}
			}
		}
	}
	return TraceContext{TraceID: randomHex(16), SpanID: randomHex(8)}
}

type OTelEvent struct {
	Name         string         `json:"name"`
	TimeUnixNano int64          `json:"time_unix_nano"`
	TraceID      string         `json:"trace_id"`
	SpanID       string         `json:"span_id"`
	Attributes   map[string]any `json:"attributes"`
}

func NewOTelEvent(result AuthorizationResult) OTelEvent {
	return OTelEvent{
		Name:         "aegis.authorization.decision",
		TimeUnixNano: result.ObservedAt.UnixNano(),
		TraceID:      result.TraceID,
		SpanID:       result.SpanID,
		Attributes: map[string]any{
			"service.name":              "aegis",
			"aegis.decision":            result.Decision,
			"aegis.reason":              result.Reason,
			"aegis.rule_id":             result.RuleID,
			"aegis.policy_hash":         result.PolicyHash,
			"aegis.signing_key_id":      result.SigningKeyID,
			"aegis.subject":             result.Subject,
			"aegis.spiffe_id":           result.SPIFFEID,
			"aegis.spiffe_trust_domain": result.TrustDomain,
			"aegis.tool":                result.Tool,
			"aegis.action":              result.Action,
			"aegis.resource":            result.Resource,
		},
	}
}

func randomHex(bytesLen int) string {
	data := make([]byte, bytesLen)
	if _, err := rand.Read(data); err != nil {
		return strings.Repeat("0", bytesLen*2)
	}
	return hex.EncodeToString(data)
}

func unixSeconds(t time.Time) int64 {
	return t.UTC().Unix()
}
