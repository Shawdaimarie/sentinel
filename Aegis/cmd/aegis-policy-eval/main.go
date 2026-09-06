package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/Shawdaimarie/sentinel/Aegis/internal/aegis"
)

type evalCase struct {
	ID               string `json:"id"`
	Subject          string `json:"subject"`
	SPIFFEID         string `json:"spiffe_id,omitempty"`
	Tool             string `json:"tool"`
	Action           string `json:"action"`
	Resource         string `json:"resource"`
	ExpectedDecision string `json:"expected_decision"`
}

type evalResult struct {
	ID               string `json:"id"`
	ExpectedDecision string `json:"expected_decision"`
	ActualDecision   string `json:"actual_decision"`
	Reason           string `json:"reason"`
	RuleID           string `json:"rule_id,omitempty"`
	Passed           bool   `json:"passed"`
}

type evalReport struct {
	PolicyHash string       `json:"policy_hash"`
	Passed     int          `json:"passed"`
	Failed     int          `json:"failed"`
	Results    []evalResult `json:"results"`
}

func main() {
	var policyPath string
	var casesPath string
	flag.StringVar(&policyPath, "policy", "examples/policy.json", "path to Aegis policy JSON")
	flag.StringVar(&casesPath, "cases", "examples/policy_eval_cases.json", "path to policy evaluation cases")
	flag.Parse()

	policy, err := aegis.LoadPolicy(policyPath)
	if err != nil {
		exitError("load policy", err)
	}
	data, err := os.ReadFile(casesPath)
	if err != nil {
		exitError("read cases", err)
	}
	var cases []evalCase
	if err := json.Unmarshal(data, &cases); err != nil {
		exitError("parse cases", err)
	}
	report := evalReport{PolicyHash: policy.Hash()}
	for _, item := range cases {
		identity, err := identityFromCase(policy, item)
		if err != nil {
			report.Failed++
			report.Results = append(report.Results, evalResult{
				ID:               item.ID,
				ExpectedDecision: item.ExpectedDecision,
				ActualDecision:   aegis.DecisionDeny,
				Reason:           "invalid_workload_identity",
			})
			continue
		}
		decision := policy.Evaluate(identity, aegis.Scope{
			Tool:     item.Tool,
			Action:   item.Action,
			Resource: item.Resource,
		})
		result := evalResult{
			ID:               item.ID,
			ExpectedDecision: item.ExpectedDecision,
			ActualDecision:   decision.Decision,
			Reason:           decision.Reason,
			RuleID:           decision.Rule.ID,
			Passed:           decision.Decision == item.ExpectedDecision,
		}
		if result.Passed {
			report.Passed++
		} else {
			report.Failed++
		}
		report.Results = append(report.Results, result)
	}
	encoded, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		exitError("encode report", err)
	}
	fmt.Println(string(encoded))
	if report.Failed > 0 {
		os.Exit(1)
	}
}

func identityFromCase(policy aegis.Policy, item evalCase) (aegis.WorkloadIdentity, error) {
	claims := aegis.CapabilityClaims{
		Issuer:   policy.Issuer,
		Subject:  item.Subject,
		Audience: aegis.Audience{policy.Audience},
		SPIFFEID: item.SPIFFEID,
	}
	return aegis.WorkloadIdentityFromClaims(claims)
}

func exitError(context string, err error) {
	fmt.Fprintf(os.Stderr, "%s: %v\n", context, err)
	os.Exit(1)
}
