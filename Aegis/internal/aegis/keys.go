package aegis

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/url"
	"os"
	"sync"
	"time"
)

type KeyStatus string

const (
	KeyActive  KeyStatus = "active"
	KeyRetired KeyStatus = "retired"
	KeyRevoked KeyStatus = "revoked"
)

type KeyRecord struct {
	KID       string
	Public    ed25519.PublicKey
	Private   ed25519.PrivateKey
	Status    KeyStatus
	NotBefore time.Time
	NotAfter  time.Time
}

type KeySet struct {
	mu        sync.RWMutex
	keys      map[string]KeyRecord
	activeKID string
}

func NewKeySet(records ...KeyRecord) (*KeySet, error) {
	set := &KeySet{keys: make(map[string]KeyRecord)}
	for _, record := range records {
		if err := set.Add(record); err != nil {
			return nil, err
		}
	}
	return set, nil
}

func GenerateKeyRecord(kid string, status KeyStatus, now time.Time) (KeyRecord, error) {
	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return KeyRecord{}, err
	}
	return KeyRecord{
		KID:       kid,
		Public:    publicKey,
		Private:   privateKey,
		Status:    status,
		NotBefore: now.Add(-time.Minute),
	}, nil
}

func (k *KeySet) Add(record KeyRecord) error {
	if record.KID == "" || len(record.Public) != ed25519.PublicKeySize {
		return ErrInvalidToken
	}
	if record.Status == "" {
		record.Status = KeyActive
	}
	k.mu.Lock()
	defer k.mu.Unlock()
	k.keys[record.KID] = record
	if record.Status == KeyActive && len(record.Private) == ed25519.PrivateKeySize {
		k.activeKID = record.KID
	}
	return nil
}

func (k *KeySet) RotateTo(kid string) error {
	k.mu.Lock()
	defer k.mu.Unlock()
	record, ok := k.keys[kid]
	if !ok {
		return ErrUnknownKey
	}
	if record.Status == KeyRevoked || len(record.Private) != ed25519.PrivateKeySize {
		return ErrRevokedKey
	}
	for currentKID, current := range k.keys {
		if current.Status == KeyActive {
			current.Status = KeyRetired
			k.keys[currentKID] = current
		}
	}
	record.Status = KeyActive
	k.keys[kid] = record
	k.activeKID = kid
	return nil
}

func (k *KeySet) Revoke(kid string) error {
	k.mu.Lock()
	defer k.mu.Unlock()
	record, ok := k.keys[kid]
	if !ok {
		return ErrUnknownKey
	}
	record.Status = KeyRevoked
	k.keys[kid] = record
	if k.activeKID == kid {
		k.activeKID = ""
	}
	return nil
}

func (k *KeySet) ActivePrivateKey() (string, ed25519.PrivateKey, error) {
	k.mu.RLock()
	defer k.mu.RUnlock()
	if k.activeKID == "" {
		return "", nil, errors.New("no active signing key")
	}
	record, ok := k.keys[k.activeKID]
	if !ok || record.Status != KeyActive || len(record.Private) != ed25519.PrivateKeySize {
		return "", nil, errors.New("active signing key unavailable")
	}
	return record.KID, record.Private, nil
}

func (k *KeySet) PublicKey(kid string, now time.Time) (ed25519.PublicKey, error) {
	k.mu.RLock()
	defer k.mu.RUnlock()
	record, ok := k.keys[kid]
	if !ok {
		return nil, ErrUnknownKey
	}
	if record.Status == KeyRevoked {
		return nil, ErrRevokedKey
	}
	if !record.NotBefore.IsZero() && now.Before(record.NotBefore) {
		return nil, ErrNotYetValid
	}
	if !record.NotAfter.IsZero() && now.After(record.NotAfter) {
		return nil, ErrRevokedKey
	}
	return append(ed25519.PublicKey(nil), record.Public...), nil
}

type JWK struct {
	KeyType string `json:"kty"`
	Curve   string `json:"crv"`
	KeyID   string `json:"kid"`
	Alg     string `json:"alg,omitempty"`
	Use     string `json:"use,omitempty"`
	X       string `json:"x"`
}

type JWKS struct {
	Keys []JWK `json:"keys"`
}

func (k *KeySet) PublicJWKS() JWKS {
	k.mu.RLock()
	defer k.mu.RUnlock()
	keys := make([]JWK, 0, len(k.keys))
	for _, record := range k.keys {
		if record.Status == KeyRevoked {
			continue
		}
		keys = append(keys, JWK{
			KeyType: "OKP",
			Curve:   "Ed25519",
			KeyID:   record.KID,
			Alg:     "EdDSA",
			Use:     "sig",
			X:       base64.RawURLEncoding.EncodeToString(record.Public),
		})
	}
	return JWKS{Keys: keys}
}

func KeySetFromJWKS(jwks JWKS) (*KeySet, error) {
	if len(jwks.Keys) == 0 {
		return nil, ErrInvalidToken
	}
	set := &KeySet{keys: make(map[string]KeyRecord)}
	seen := make(map[string]struct{}, len(jwks.Keys))
	for _, key := range jwks.Keys {
		if key.KeyType != "OKP" || key.Curve != "Ed25519" || key.KeyID == "" {
			return nil, ErrInvalidToken
		}
		if _, ok := seen[key.KeyID]; ok {
			return nil, ErrInvalidToken
		}
		seen[key.KeyID] = struct{}{}
		if key.Alg != "" && key.Alg != "EdDSA" {
			return nil, ErrInvalidToken
		}
		if key.Use != "" && key.Use != "sig" {
			return nil, ErrInvalidToken
		}
		publicKey, err := base64.RawURLEncoding.DecodeString(key.X)
		if err != nil || len(publicKey) != ed25519.PublicKeySize {
			return nil, ErrInvalidToken
		}
		if err := set.Add(KeyRecord{
			KID:    key.KeyID,
			Public: ed25519.PublicKey(publicKey),
			Status: KeyActive,
		}); err != nil {
			return nil, err
		}
	}
	return set, nil
}

func LoadJWKS(path string) (*KeySet, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var jwks JWKS
	if err := json.Unmarshal(data, &jwks); err != nil {
		return nil, err
	}
	return KeySetFromJWKS(jwks)
}

type TrustedIssuerConfig struct {
	Issuer  string `json:"issuer"`
	JWKSURI string `json:"jwks_uri,omitempty"`
	JWKS    JWKS   `json:"jwks"`
}

type TrustBundle struct {
	Issuers []TrustedIssuerConfig `json:"issuers"`
}

type IssuerKeySet struct {
	mu      sync.RWMutex
	issuers map[string]*KeySet
}

func NewIssuerKeySet() *IssuerKeySet {
	return &IssuerKeySet{issuers: make(map[string]*KeySet)}
}

func NewIssuerKeySetFromKeySet(issuer string, keys *KeySet) (*IssuerKeySet, error) {
	set := NewIssuerKeySet()
	if err := set.AddIssuer(issuer, keys); err != nil {
		return nil, err
	}
	return set, nil
}

func IssuerKeySetFromTrustBundle(bundle TrustBundle) (*IssuerKeySet, error) {
	if len(bundle.Issuers) == 0 {
		return nil, ErrUntrustedIssuer
	}
	set := NewIssuerKeySet()
	for _, config := range bundle.Issuers {
		if config.JWKSURI != "" && !isHTTPSIssuerURL(config.JWKSURI) {
			return nil, ErrUntrustedIssuer
		}
		keys, err := KeySetFromJWKS(config.JWKS)
		if err != nil {
			return nil, err
		}
		if err := set.AddIssuer(config.Issuer, keys); err != nil {
			return nil, err
		}
	}
	return set, nil
}

func LoadTrustBundle(path string) (*IssuerKeySet, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var bundle TrustBundle
	if err := json.Unmarshal(data, &bundle); err != nil {
		return nil, err
	}
	return IssuerKeySetFromTrustBundle(bundle)
}

func (s *IssuerKeySet) AddIssuer(issuer string, keys *KeySet) error {
	if keys == nil || !isHTTPSIssuerURL(issuer) {
		return ErrUntrustedIssuer
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.issuers[issuer]; ok {
		return ErrUntrustedIssuer
	}
	s.issuers[issuer] = keys
	return nil
}

func (s *IssuerKeySet) KeySet(issuer string) (*KeySet, error) {
	if s == nil {
		return nil, ErrUntrustedIssuer
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	keys, ok := s.issuers[issuer]
	if !ok || keys == nil {
		return nil, ErrUntrustedIssuer
	}
	return keys, nil
}

func (s *IssuerKeySet) VerifyCapability(token string, expectedIssuer string, now time.Time) (VerifiedCapability, error) {
	keys, err := s.keysForTokenIssuer(token, expectedIssuer)
	if err != nil {
		return VerifiedCapability{}, err
	}
	return keys.VerifyCapability(token, now)
}

func (s *IssuerKeySet) VerifyApproval(token string, expectedIssuer string, now time.Time) (VerifiedApproval, error) {
	keys, err := s.keysForTokenIssuer(token, expectedIssuer)
	if err != nil {
		return VerifiedApproval{}, err
	}
	return keys.VerifyApproval(token, now)
}

func (s *IssuerKeySet) keysForTokenIssuer(token string, expectedIssuer string) (*KeySet, error) {
	issuer, err := unverifiedIssuer(token)
	if err != nil {
		return nil, err
	}
	if issuer != expectedIssuer {
		return nil, ErrUntrustedIssuer
	}
	return s.KeySet(issuer)
}

func isHTTPSIssuerURL(value string) bool {
	parsed, err := url.Parse(value)
	return err == nil && parsed.Scheme == "https" && parsed.Host != "" &&
		parsed.RawQuery == "" && parsed.Fragment == ""
}
