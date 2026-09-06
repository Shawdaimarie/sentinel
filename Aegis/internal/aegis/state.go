package aegis

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type StateStore interface {
	Health(context.Context) error
	ReserveJTI(context.Context, string, time.Time) error
	ReserveRateLimit(context.Context, string, RateLimitSpec, time.Time) error
	RevokeJTI(context.Context, string, string, time.Time) error
	RevokeSubject(context.Context, string, string) error
	IsSubjectRevoked(context.Context, string) (bool, error)
}

type stateEntry struct {
	ExpiresAt time.Time
	Reason    string
}

type MemoryStateStore struct {
	mu              sync.Mutex
	usedJTIs        map[string]time.Time
	revokedJTIs     map[string]stateEntry
	revokedSubjects map[string]string
	rateBuckets      map[string]rateBucket
	healthErr       error
	reserveErr      error
	rateLimitErr    error
	clock           Clock
}

func NewMemoryStateStore() *MemoryStateStore {
	return &MemoryStateStore{
		usedJTIs:        make(map[string]time.Time),
		revokedJTIs:     make(map[string]stateEntry),
		revokedSubjects: make(map[string]string),
		rateBuckets:     make(map[string]rateBucket),
		clock:           RealClock{},
	}
}

func (m *MemoryStateStore) Health(context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.healthErr != nil {
		return m.healthErr
	}
	return nil
}

func (m *MemoryStateStore) ReserveJTI(_ context.Context, jti string, expiresAt time.Time) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	now := m.now()
	if m.reserveErr != nil {
		return m.reserveErr
	}
	m.gc(now)
	if _, ok := m.revokedJTIs[jti]; ok {
		return ErrRevoked
	}
	if previousExpiry, ok := m.usedJTIs[jti]; ok && now.Before(previousExpiry) {
		return ErrReplay
	}
	m.usedJTIs[jti] = expiresAt
	return nil
}

func (m *MemoryStateStore) ReserveRateLimit(_ context.Context, key string, spec RateLimitSpec, now time.Time) error {
	if spec.Limit <= 0 || spec.WindowSeconds <= 0 {
		return nil
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.rateLimitErr != nil {
		return m.rateLimitErr
	}
	bucket := m.rateBuckets[key]
	if bucket.ResetAt.IsZero() || !now.Before(bucket.ResetAt) {
		bucket = rateBucket{ResetAt: now.Add(time.Duration(spec.WindowSeconds) * time.Second)}
	}
	if bucket.Count >= spec.Limit {
		m.rateBuckets[key] = bucket
		return ErrRateLimited
	}
	bucket.Count++
	m.rateBuckets[key] = bucket
	return nil
}

func (m *MemoryStateStore) RevokeJTI(_ context.Context, jti string, reason string, expiresAt time.Time) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.revokedJTIs[jti] = stateEntry{ExpiresAt: expiresAt, Reason: reason}
	return nil
}

func (m *MemoryStateStore) RevokeSubject(_ context.Context, subject string, reason string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.revokedSubjects[subject] = reason
	return nil
}

func (m *MemoryStateStore) IsSubjectRevoked(_ context.Context, subject string) (bool, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	_, ok := m.revokedSubjects[subject]
	return ok, nil
}

func (m *MemoryStateStore) InjectHealthFailure(err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.healthErr = err
}

func (m *MemoryStateStore) InjectReserveFailure(err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.reserveErr = err
}

func (m *MemoryStateStore) InjectRateLimitFailure(err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.rateLimitErr = err
}

func (m *MemoryStateStore) SetClock(clock Clock) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.clock = clock
}

func (m *MemoryStateStore) now() time.Time {
	if m.clock == nil {
		return time.Now().UTC()
	}
	return m.clock.Now().UTC()
}

func (m *MemoryStateStore) gc(now time.Time) {
	for jti, expiresAt := range m.usedJTIs {
		if !now.Before(expiresAt) {
			delete(m.usedJTIs, jti)
		}
	}
	for jti, entry := range m.revokedJTIs {
		if !entry.ExpiresAt.IsZero() && !now.Before(entry.ExpiresAt) {
			delete(m.revokedJTIs, jti)
		}
	}
}

type stateEvent struct {
	Type      string `json:"type"`
	JTI       string `json:"jti,omitempty"`
	Subject   string `json:"subject,omitempty"`
	RateKey   string `json:"rate_key,omitempty"`
	Reason    string `json:"reason,omitempty"`
	ExpiresAt int64  `json:"expires_at,omitempty"`
	ResetAt   int64  `json:"reset_at,omitempty"`
	At        int64  `json:"at"`
}

type FileStateStore struct {
	memory *MemoryStateStore
	path   string
	mu     sync.Mutex
}

func NewFileStateStore(path string) (*FileStateStore, error) {
	store := &FileStateStore{memory: NewMemoryStateStore(), path: path}
	if err := store.load(); err != nil {
		return nil, err
	}
	return store, nil
}

func (f *FileStateStore) Health(ctx context.Context) error {
	return f.memory.Health(ctx)
}

func (f *FileStateStore) ReserveJTI(ctx context.Context, jti string, expiresAt time.Time) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	if err := f.memory.ReserveJTI(ctx, jti, expiresAt); err != nil {
		return err
	}
	return f.append(stateEvent{
		Type:      "reserve_jti",
		JTI:       jti,
		ExpiresAt: expiresAt.Unix(),
		At:        time.Now().UTC().Unix(),
	})
}

func (f *FileStateStore) ReserveRateLimit(ctx context.Context, key string, spec RateLimitSpec, now time.Time) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	if err := f.memory.ReserveRateLimit(ctx, key, spec, now); err != nil {
		return err
	}
	if spec.Limit <= 0 || spec.WindowSeconds <= 0 {
		return nil
	}
	f.memory.mu.Lock()
	bucket := f.memory.rateBuckets[key]
	f.memory.mu.Unlock()
	return f.append(stateEvent{
		Type:    "reserve_rate_limit",
		RateKey: key,
		ResetAt: bucket.ResetAt.Unix(),
		At:      time.Now().UTC().Unix(),
	})
}

func (f *FileStateStore) RevokeJTI(ctx context.Context, jti string, reason string, expiresAt time.Time) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	if err := f.memory.RevokeJTI(ctx, jti, reason, expiresAt); err != nil {
		return err
	}
	return f.append(stateEvent{
		Type:      "revoke_jti",
		JTI:       jti,
		Reason:    reason,
		ExpiresAt: expiresAt.Unix(),
		At:        time.Now().UTC().Unix(),
	})
}

func (f *FileStateStore) RevokeSubject(ctx context.Context, subject string, reason string) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	if err := f.memory.RevokeSubject(ctx, subject, reason); err != nil {
		return err
	}
	return f.append(stateEvent{
		Type:    "revoke_subject",
		Subject: subject,
		Reason:  reason,
		At:      time.Now().UTC().Unix(),
	})
}

func (f *FileStateStore) IsSubjectRevoked(ctx context.Context, subject string) (bool, error) {
	return f.memory.IsSubjectRevoked(ctx, subject)
}

func (f *FileStateStore) load() error {
	file, err := os.Open(f.path)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		var event stateEvent
		if err := json.Unmarshal(scanner.Bytes(), &event); err != nil {
			return err
		}
		switch event.Type {
		case "reserve_jti":
			f.memory.usedJTIs[event.JTI] = time.Unix(event.ExpiresAt, 0)
		case "reserve_rate_limit":
			f.loadRateLimitReservation(event)
		case "revoke_jti":
			f.memory.revokedJTIs[event.JTI] = stateEntry{
				ExpiresAt: time.Unix(event.ExpiresAt, 0),
				Reason:    event.Reason,
			}
		case "revoke_subject":
			f.memory.revokedSubjects[event.Subject] = event.Reason
		}
	}
	return scanner.Err()
}

func (f *FileStateStore) loadRateLimitReservation(event stateEvent) {
	if event.RateKey == "" || event.ResetAt <= 0 {
		return
	}
	resetAt := time.Unix(event.ResetAt, 0)
	bucket := f.memory.rateBuckets[event.RateKey]
	switch {
	case bucket.ResetAt.Equal(resetAt):
		bucket.Count++
	case bucket.ResetAt.IsZero() || !resetAt.Before(bucket.ResetAt):
		bucket = rateBucket{Count: 1, ResetAt: resetAt}
	default:
		return
	}
	f.memory.rateBuckets[event.RateKey] = bucket
}

func (f *FileStateStore) append(event stateEvent) error {
	if err := os.MkdirAll(filepath.Dir(f.path), 0o750); err != nil {
		return err
	}
	file, err := os.OpenFile(f.path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	defer file.Close()
	encoded, err := json.Marshal(event)
	if err != nil {
		return err
	}
	if _, err := file.Write(append(encoded, '\n')); err != nil {
		return err
	}
	return file.Sync()
}
