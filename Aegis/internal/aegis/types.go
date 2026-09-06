package aegis

import (
	"encoding/json"
	"errors"
	"net/url"
	"strings"
	"time"
)

const (
	DecisionAllow = "allow"
	DecisionDeny  = "deny"
)

var (
	ErrInvalidToken     = errors.New("invalid token")
	ErrUntrustedIssuer  = errors.New("untrusted issuer")
	ErrUnknownKey       = errors.New("unknown signing key")
	ErrRevokedKey       = errors.New("revoked signing key")
	ErrExpiredToken     = errors.New("expired token")
	ErrNotYetValid      = errors.New("token is not yet valid")
	ErrInvalidIdentity  = errors.New("invalid workload identity")
	ErrReplay           = errors.New("capability replay detected")
	ErrRevoked          = errors.New("capability or principal is revoked")
	ErrStateUnavailable = errors.New("state store unavailable")
	ErrRateLimited      = errors.New("rate limit exceeded")
)

type Clock interface {
	Now() time.Time
}

type RealClock struct{}

func (RealClock) Now() time.Time {
	return time.Now().UTC()
}

type Audience []string

func (a Audience) Contains(want string) bool {
	for _, got := range a {
		if got == want {
			return true
		}
	}
	return false
}

func (a *Audience) UnmarshalJSON(data []byte) error {
	var single string
	if err := json.Unmarshal(data, &single); err == nil {
		*a = Audience{single}
		return nil
	}
	var many []string
	if err := json.Unmarshal(data, &many); err != nil {
		return err
	}
	*a = Audience(many)
	return nil
}

type CapabilityClaims struct {
	Issuer     string   `json:"iss"`
	Subject    string   `json:"sub"`
	Audience   Audience `json:"aud"`
	ExpiresAt  int64    `json:"exp"`
	NotBefore  int64    `json:"nbf,omitempty"`
	IssuedAt   int64    `json:"iat"`
	JTI        string   `json:"jti"`
	Tool       string   `json:"tool"`
	Action     string   `json:"action"`
	Resource   string   `json:"resource"`
	PolicyHash string   `json:"policy_hash"`
	SPIFFEID   string   `json:"spiffe_id,omitempty"`
}

func (c CapabilityClaims) Validate(now time.Time, issuer string, audience string) error {
	if c.Issuer != issuer || !c.Audience.Contains(audience) {
		return ErrInvalidToken
	}
	if c.Subject == "" || c.JTI == "" || c.Tool == "" || c.Action == "" || c.Resource == "" {
		return ErrInvalidToken
	}
	if c.PolicyHash == "" || c.IssuedAt <= 0 || c.ExpiresAt <= 0 {
		return ErrInvalidToken
	}
	if !now.Before(time.Unix(c.ExpiresAt, 0)) {
		return ErrExpiredToken
	}
	if c.NotBefore > 0 && now.Before(time.Unix(c.NotBefore, 0)) {
		return ErrNotYetValid
	}
	if c.IssuedAt > now.Add(2*time.Minute).Unix() {
		return ErrNotYetValid
	}
	return nil
}

func (c CapabilityClaims) Scope() Scope {
	return Scope{Tool: c.Tool, Action: c.Action, Resource: c.Resource}
}

type ApprovalClaims struct {
	Issuer              string   `json:"iss"`
	Subject             string   `json:"sub"`
	Audience            Audience `json:"aud"`
	ExpiresAt           int64    `json:"exp"`
	IssuedAt            int64    `json:"iat"`
	JTI                 string   `json:"jti"`
	CapabilityJTI       string   `json:"capability_jti"`
	CapabilitySHA256    string   `json:"capability_sha256"`
	Tool                string   `json:"tool"`
	Action              string   `json:"action"`
	Resource            string   `json:"resource"`
	PolicyHash          string   `json:"policy_hash"`
	ApprovedBy          string   `json:"approved_by"`
	ApprovalEvidenceURI string   `json:"approval_evidence_uri,omitempty"`
}

func (a ApprovalClaims) Validate(now time.Time, issuer string, audience string) error {
	if a.Issuer != issuer || !a.Audience.Contains(audience) {
		return ErrInvalidToken
	}
	if a.Subject == "" || a.JTI == "" || a.CapabilityJTI == "" || a.CapabilitySHA256 == "" {
		return ErrInvalidToken
	}
	if a.Tool == "" || a.Action == "" || a.Resource == "" || a.PolicyHash == "" || a.ApprovedBy == "" {
		return ErrInvalidToken
	}
	if !now.Before(time.Unix(a.ExpiresAt, 0)) {
		return ErrExpiredToken
	}
	if a.IssuedAt > now.Add(2*time.Minute).Unix() {
		return ErrNotYetValid
	}
	return nil
}

type Scope struct {
	Tool     string
	Action   string
	Resource string
}

type WorkloadIdentity struct {
	Subject     string
	Issuer      string
	Audience    Audience
	SPIFFEID    string
	TrustDomain string
}

func WorkloadIdentityFromClaims(claims CapabilityClaims) (WorkloadIdentity, error) {
	subjectSPIFFEID := ""
	if strings.HasPrefix(claims.Subject, "spiffe://") {
		subjectSPIFFEID = claims.Subject
		if _, err := ParseSPIFFETrustDomain(subjectSPIFFEID); err != nil {
			return WorkloadIdentity{}, err
		}
	}
	spiffeID := claims.SPIFFEID
	if spiffeID != "" && subjectSPIFFEID != "" && spiffeID != subjectSPIFFEID {
		return WorkloadIdentity{}, ErrInvalidIdentity
	}
	if spiffeID == "" {
		spiffeID = subjectSPIFFEID
	}
	trustDomain := ""
	if spiffeID != "" {
		var err error
		trustDomain, err = ParseSPIFFETrustDomain(spiffeID)
		if err != nil {
			return WorkloadIdentity{}, err
		}
	}
	return WorkloadIdentity{
		Subject:     claims.Subject,
		Issuer:      claims.Issuer,
		Audience:    claims.Audience,
		SPIFFEID:    spiffeID,
		TrustDomain: trustDomain,
	}, nil
}

func ParseSPIFFETrustDomain(spiffeID string) (string, error) {
	parsed, err := url.Parse(spiffeID)
	if err != nil {
		return "", ErrInvalidIdentity
	}
	if parsed.Scheme != "spiffe" || parsed.Host == "" || parsed.Path == "" {
		return "", ErrInvalidIdentity
	}
	if parsed.RawQuery != "" || parsed.Fragment != "" || strings.Contains(parsed.Path, "..") {
		return "", ErrInvalidIdentity
	}
	return parsed.Host, nil
}
