package aegis

import (
	"bufio"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

type AuditSink interface {
	Append(context.Context, AuthorizationResult) (int64, string, error)
}

type DecisionRecord struct {
	Sequence    int64  `json:"sequence"`
	Timestamp   string `json:"timestamp"`
	Decision    string `json:"decision"`
	Reason      string `json:"reason"`
	Subject     string `json:"subject,omitempty"`
	SPIFFEID    string `json:"spiffe_id,omitempty"`
	TrustDomain string `json:"trust_domain,omitempty"`
	Tool        string `json:"tool,omitempty"`
	Action      string `json:"action,omitempty"`
	Resource    string `json:"resource,omitempty"`
	RuleID      string `json:"rule_id,omitempty"`
	PolicyHash  string `json:"policy_hash,omitempty"`
	SigningKey  string `json:"signing_key_id,omitempty"`
	TraceID     string `json:"trace_id,omitempty"`
	SpanID      string `json:"span_id,omitempty"`
	Previous    string `json:"previous_hash"`
	RecordHash  string `json:"record_hash"`
}

type MemoryAuditLog struct {
	mu       sync.Mutex
	records  []DecisionRecord
	previous string
}

func NewMemoryAuditLog() *MemoryAuditLog {
	return &MemoryAuditLog{}
}

func (m *MemoryAuditLog) Append(_ context.Context, result AuthorizationResult) (int64, string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	record := result.toRecord(int64(len(m.records)+1), m.previous)
	record.RecordHash = hashRecord(record)
	m.records = append(m.records, record)
	m.previous = record.RecordHash
	return record.Sequence, record.RecordHash, nil
}

func (m *MemoryAuditLog) Records() []DecisionRecord {
	m.mu.Lock()
	defer m.mu.Unlock()
	return append([]DecisionRecord(nil), m.records...)
}

type FileAuditLog struct {
	mu       sync.Mutex
	path     string
	sequence int64
	previous string
}

func NewFileAuditLog(path string) (*FileAuditLog, error) {
	log := &FileAuditLog{path: path}
	if err := log.load(); err != nil {
		return nil, err
	}
	return log, nil
}

func (f *FileAuditLog) Append(_ context.Context, result AuthorizationResult) (int64, string, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	record := result.toRecord(f.sequence+1, f.previous)
	record.RecordHash = hashRecord(record)
	if err := os.MkdirAll(filepath.Dir(f.path), 0o750); err != nil {
		return 0, "", err
	}
	file, err := os.OpenFile(f.path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return 0, "", err
	}
	defer file.Close()
	encoded, err := json.Marshal(record)
	if err != nil {
		return 0, "", err
	}
	if _, err := file.Write(append(encoded, '\n')); err != nil {
		return 0, "", err
	}
	if err := file.Sync(); err != nil {
		return 0, "", err
	}
	f.sequence = record.Sequence
	f.previous = record.RecordHash
	return record.Sequence, record.RecordHash, nil
}

func (f *FileAuditLog) load() error {
	file, err := os.Open(f.path)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		var record DecisionRecord
		if err := json.Unmarshal(scanner.Bytes(), &record); err != nil {
			return err
		}
		if record.Sequence != f.sequence+1 || record.Previous != f.previous {
			return ErrInvalidToken
		}
		if hashRecord(record) != record.RecordHash {
			return ErrInvalidToken
		}
		f.sequence = record.Sequence
		f.previous = record.RecordHash
	}
	return scanner.Err()
}

func (r AuthorizationResult) toRecord(sequence int64, previous string) DecisionRecord {
	return DecisionRecord{
		Sequence:    sequence,
		Timestamp:   r.ObservedAt.UTC().Format("2006-01-02T15:04:05.000000000Z"),
		Decision:    r.Decision,
		Reason:      r.Reason,
		Subject:     r.Subject,
		SPIFFEID:    r.SPIFFEID,
		TrustDomain: r.TrustDomain,
		Tool:        r.Tool,
		Action:      r.Action,
		Resource:    r.Resource,
		RuleID:      r.RuleID,
		PolicyHash:  r.PolicyHash,
		SigningKey:  r.SigningKeyID,
		TraceID:     r.TraceID,
		SpanID:      r.SpanID,
		Previous:    previous,
	}
}

func hashRecord(record DecisionRecord) string {
	record.RecordHash = ""
	data, _ := json.Marshal(record)
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}
