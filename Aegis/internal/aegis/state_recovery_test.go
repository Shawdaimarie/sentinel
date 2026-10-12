package aegis

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestFileStateStoreRejectsUnknownEventsWithoutChangingEvidence(t *testing.T) {
	for name, invalid := range map[string]string{
		"unknown event":          `{"type":"future_event","subject":"private-subject"}`,
		"misspelled reservation": `{"type":"reserve_jit","jti":"private-capability","expires_at":2000000000}`,
		"missing type":           `{"subject":"private-subject"}`,
		"empty object":           `{}`,
		"null":                   `null`,
	} {
		t.Run(name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "state.jsonl")
			first, err := NewFileStateStore(path)
			if err != nil {
				t.Fatal(err)
			}
			if err := first.RevokeSubject(context.Background(), "already-revoked", "incident"); err != nil {
				t.Fatal(err)
			}
			original, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			evidence := append(original, []byte(invalid+"\n")...)
			if err := os.WriteFile(path, evidence, 0o600); err != nil {
				t.Fatal(err)
			}

			restarted, err := NewFileStateStore(path)
			if err == nil || restarted != nil {
				t.Fatal("state recovery accepted an unsupported event after a valid record")
			}
			if !strings.Contains(err.Error(), "state log line 2: unsupported event type") {
				t.Fatalf("expected a line-specific recovery error, got %v", err)
			}
			if strings.Contains(err.Error(), "private-") {
				t.Fatalf("recovery error disclosed record contents: %v", err)
			}
			after, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(after, evidence) {
				t.Fatal("failed recovery changed the original state log")
			}
		})
	}
}

func TestFileStateStoreReloadsEverySupportedEvent(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC().Truncate(time.Second)
	expires := now.Add(time.Hour)
	path := filepath.Join(t.TempDir(), "state.jsonl")
	first, err := NewFileStateStore(path)
	if err != nil {
		t.Fatal(err)
	}
	first.memory.SetClock(staticClock{now: now})
	spec := RateLimitSpec{Limit: 1, WindowSeconds: 60}
	for _, err := range []error{
		first.ReserveJTI(ctx, "used-capability", expires),
		first.RevokeJTI(ctx, "revoked-capability", "incident", expires),
		first.RevokeSubject(ctx, "revoked-subject", "incident"),
		first.ReserveRateLimit(ctx, "workload|tool|action", spec, now),
	} {
		if err != nil {
			t.Fatal(err)
		}
	}
	restarted, err := NewFileStateStore(path)
	if err != nil {
		t.Fatal(err)
	}
	restarted.memory.SetClock(staticClock{now: now})
	if err := restarted.ReserveJTI(ctx, "used-capability", expires); !errors.Is(err, ErrReplay) {
		t.Fatalf("used capability was not preserved: %v", err)
	}
	if err := restarted.ReserveJTI(ctx, "revoked-capability", expires); !errors.Is(err, ErrRevoked) {
		t.Fatalf("capability revocation was not preserved: %v", err)
	}
	if revoked, err := restarted.IsSubjectRevoked(ctx, "revoked-subject"); err != nil || !revoked {
		t.Fatalf("subject revocation was not preserved: revoked=%v, err=%v", revoked, err)
	}
	if err := restarted.ReserveRateLimit(ctx, "workload|tool|action", spec, now); !errors.Is(err, ErrRateLimited) {
		t.Fatalf("rate reservation was not preserved: %v", err)
	}
}
