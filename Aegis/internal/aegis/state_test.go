package aegis

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"
)

func TestFileStateStorePersistsRateLimitReservationsAcrossRestart(t *testing.T) {
	path := filepath.Join(t.TempDir(), "aegis-state.jsonl")
	key := "spiffe://example.org/ns/finance/sa/sentinel-agent|mcp.billing|read"
	spec := RateLimitSpec{Limit: 1, WindowSeconds: 60}
	now := time.Date(2026, 9, 5, 12, 0, 0, 0, time.UTC)

	first, err := NewFileStateStore(path)
	if err != nil {
		t.Fatal(err)
	}
	if err := first.ReserveRateLimit(context.Background(), key, spec, now); err != nil {
		t.Fatalf("expected first reservation to succeed: %v", err)
	}

	restarted, err := NewFileStateStore(path)
	if err != nil {
		t.Fatal(err)
	}
	err = restarted.ReserveRateLimit(context.Background(), key, spec, now.Add(10*time.Second))
	if !errors.Is(err, ErrRateLimited) {
		t.Fatalf("expected persisted quota to deny after restart, got %v", err)
	}
	if err := restarted.ReserveRateLimit(context.Background(), key, spec, now.Add(61*time.Second)); err != nil {
		t.Fatalf("expected quota reset after window, got %v", err)
	}
}
