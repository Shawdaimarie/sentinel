package aegis

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"sort"
	"strings"
)

type Policy struct {
	Version              string `json:"version"`
	Issuer               string `json:"issuer"`
	Audience             string `json:"audience"`
	DefaultMaxTTLSeconds int    `json:"default_max_ttl_seconds"`
	Rules                []Rule `json:"rules"`
}

type Rule struct {
	ID                 string         `json:"id"`
	Effect             string         `json:"effect"`
	Subjects           []string       `json:"subjects"`
	SPIFFETrustDomains []string       `json:"spiffe_trust_domains,omitempty"`
	Tools              []string       `json:"tools"`
	Actions            []string       `json:"actions"`
	Resources          []string       `json:"resources"`
	RequireApproval    bool           `json:"require_approval,omitempty"`
	MaxTTLSeconds      int            `json:"max_ttl_seconds,omitempty"`
	RateLimit          *RateLimitSpec `json:"rate_limit,omitempty"`
}

type PolicyDecision struct {
	Decision string
	Reason   string
	Rule     Rule
}

func LoadPolicy(path string) (Policy, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Policy{}, err
	}
	var policy Policy
	if err := json.Unmarshal(data, &policy); err != nil {
		return Policy{}, err
	}
	return policy, nil
}

func (p Policy) Hash() string {
	normalized := p.normalized()
	data, _ := json.Marshal(normalized)
	sum := sha256.Sum256(data)
	return "sha256:" + hex.EncodeToString(sum[:])
}

func (p Policy) Evaluate(identity WorkloadIdentity, scope Scope) PolicyDecision {
	bestSpecificity := -1
	var best Rule
	matched := false
	for _, rule := range p.Rules {
		if ok, specificity := rule.matches(identity, scope); ok {
			if !matched || specificity > bestSpecificity {
				matched = true
				bestSpecificity = specificity
				best = rule
				continue
			}
			if specificity == bestSpecificity && rule.Effect == "deny" {
				best = rule
			}
		}
	}
	if !matched {
		return PolicyDecision{Decision: DecisionDeny, Reason: "policy_no_match"}
	}
	if best.Effect != "allow" {
		return PolicyDecision{Decision: DecisionDeny, Reason: "policy_deny_rule", Rule: best}
	}
	return PolicyDecision{Decision: DecisionAllow, Reason: "policy_allow", Rule: best}
}

func (r Rule) matches(identity WorkloadIdentity, scope Scope) (bool, int) {
	subjectOK, subjectScore := matchIdentity(r, identity)
	if !subjectOK {
		return false, 0
	}
	toolOK, toolScore := bestPatternMatch(r.Tools, scope.Tool)
	actionOK, actionScore := bestPatternMatch(r.Actions, scope.Action)
	resourceOK, resourceScore := bestPatternMatch(r.Resources, scope.Resource)
	if !toolOK || !actionOK || !resourceOK {
		return false, 0
	}
	return true, subjectScore + toolScore + actionScore + resourceScore
}

func matchIdentity(rule Rule, identity WorkloadIdentity) (bool, int) {
	score := 0
	if len(rule.Subjects) > 0 {
		bestSubject := -1
		for _, candidate := range []string{identity.Subject, identity.SPIFFEID} {
			if candidate == "" {
				continue
			}
			if ok, candidateScore := bestPatternMatch(rule.Subjects, candidate); ok && candidateScore > bestSubject {
				bestSubject = candidateScore
			}
		}
		if bestSubject < 0 {
			return false, 0
		}
		score += bestSubject
	}
	if len(rule.SPIFFETrustDomains) > 0 {
		bestTrustDomain := -1
		for _, trustDomain := range rule.SPIFFETrustDomains {
			if trustDomain == identity.TrustDomain && trustDomain != "" {
				candidateScore := 200 + len(trustDomain)
				if candidateScore > bestTrustDomain {
					bestTrustDomain = candidateScore
				}
			}
		}
		if bestTrustDomain < 0 {
			return false, 0
		}
		score += bestTrustDomain
	}
	return len(rule.Subjects) > 0 || len(rule.SPIFFETrustDomains) > 0, score
}

func bestPatternMatch(patterns []string, value string) (bool, int) {
	best := -1
	for _, pattern := range patterns {
		if ok, score := patternMatch(pattern, value); ok && score > best {
			best = score
		}
	}
	return best >= 0, best
}

func patternMatch(pattern string, value string) (bool, int) {
	if pattern == "" || value == "" {
		return false, 0
	}
	if pattern == value {
		return true, 1000 + len(pattern)
	}
	if pattern == "*" {
		return true, 1
	}
	if strings.Count(pattern, "*") != 1 || !strings.HasSuffix(pattern, "*") {
		return false, 0
	}
	prefix := strings.TrimSuffix(pattern, "*")
	if prefix == "" || !strings.HasPrefix(value, prefix) {
		return false, 0
	}
	return true, len(prefix)
}

func (p Policy) normalized() Policy {
	normalized := p
	normalized.Rules = append([]Rule(nil), p.Rules...)
	for i := range normalized.Rules {
		sort.Strings(normalized.Rules[i].Subjects)
		sort.Strings(normalized.Rules[i].SPIFFETrustDomains)
		sort.Strings(normalized.Rules[i].Tools)
		sort.Strings(normalized.Rules[i].Actions)
		sort.Strings(normalized.Rules[i].Resources)
	}
	sort.Slice(normalized.Rules, func(i int, j int) bool {
		return normalized.Rules[i].ID < normalized.Rules[j].ID
	})
	return normalized
}
