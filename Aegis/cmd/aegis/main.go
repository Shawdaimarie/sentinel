package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Shawdaimarie/sentinel/Aegis/internal/aegis"
)

func main() {
	var policyPath string
	var jwksPath string
	var trustBundlePath string
	var listenAddr string
	var auditPath string
	var statePath string
	var checkConfig bool
	flag.StringVar(&policyPath, "policy", "examples/policy.json", "path to Aegis policy JSON")
	flag.StringVar(&jwksPath, "jwks", "examples/jwks.json", "path to public Ed25519 JWKS")
	flag.StringVar(&trustBundlePath, "trust-bundle", "", "optional issuer-scoped JWKS trust bundle JSON")
	flag.StringVar(&listenAddr, "listen", "127.0.0.1:8080", "safe listen address")
	flag.StringVar(&auditPath, "audit-log", "audit/aegis-decisions.jsonl", "decision audit JSONL path")
	flag.StringVar(&statePath, "state-log", "audit/aegis-state.jsonl", "replay and revocation state JSONL path")
	flag.BoolVar(&checkConfig, "check-config", false, "load configuration and exit")
	flag.Parse()

	policy, err := aegis.LoadPolicy(policyPath)
	if err != nil {
		log.Fatalf("load policy: %v", err)
	}
	keys, trustedIssuers, err := loadVerifierKeys(policy, jwksPath, trustBundlePath)
	if err != nil {
		log.Fatalf("load verifier keys: %v", err)
	}
	state, err := aegis.NewFileStateStore(statePath)
	if err != nil {
		log.Fatalf("load state: %v", err)
	}
	audit, err := aegis.NewFileAuditLog(auditPath)
	if err != nil {
		log.Fatalf("load audit: %v", err)
	}
	authorizer := aegis.NewAuthorizer(policy, keys, state, audit)
	authorizer.TrustedIssuers = trustedIssuers
	if checkConfig {
		log.Printf("aegis config ok: issuer=%s", policy.Issuer)
		return
	}
	server := aegis.NewHTTPServer(aegis.HTTPHandler{
		Authorizer: authorizer,
		Config: aegis.HTTPConfig{
			Issuer:     policy.Issuer,
			ListenAddr: listenAddr,
		},
	})
	errs := make(chan error, 1)
	go func() {
		log.Printf("aegis listening on %s", listenAddr)
		errs <- server.ListenAndServe()
	}()
	signals := make(chan os.Signal, 1)
	signal.Notify(signals, syscall.SIGINT, syscall.SIGTERM)
	select {
	case sig := <-signals:
		log.Printf("shutting down after %s", sig)
	case err := <-errs:
		if err != nil && err != http.ErrServerClosed {
			log.Fatalf("server failed: %v", err)
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		fmt.Fprintf(os.Stderr, "shutdown failed: %v\n", err)
		os.Exit(1)
	}
}

func loadVerifierKeys(policy aegis.Policy, jwksPath string, trustBundlePath string) (*aegis.KeySet, *aegis.IssuerKeySet, error) {
	if trustBundlePath == "" {
		keys, err := aegis.LoadJWKS(jwksPath)
		if err != nil {
			return nil, nil, err
		}
		trustedIssuers, err := aegis.NewIssuerKeySetFromKeySet(policy.Issuer, keys)
		if err != nil {
			return nil, nil, err
		}
		return keys, trustedIssuers, nil
	}
	trustedIssuers, err := aegis.LoadTrustBundle(trustBundlePath)
	if err != nil {
		return nil, nil, err
	}
	keys, err := trustedIssuers.KeySet(policy.Issuer)
	if err != nil {
		return nil, nil, err
	}
	return keys, trustedIssuers, nil
}
