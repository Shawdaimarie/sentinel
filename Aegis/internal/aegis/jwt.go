package aegis

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

type protectedHeader struct {
	Type      string `json:"typ"`
	Alg       string `json:"alg"`
	KeyID     string `json:"kid"`
	TokenKind string `json:"token_kind,omitempty"`
}

type VerifiedCapability struct {
	Header     protectedHeader
	Claims     CapabilityClaims
	SigningKey string
	TokenHash  string
}

type VerifiedApproval struct {
	Header     protectedHeader
	Claims     ApprovalClaims
	SigningKey string
	TokenHash  string
}

func signJWT(privateKey ed25519.PrivateKey, kid string, tokenKind string, claims any) (string, error) {
	header := protectedHeader{
		Type:      "JWT",
		Alg:       "EdDSA",
		KeyID:     kid,
		TokenKind: tokenKind,
	}
	headerJSON, err := json.Marshal(header)
	if err != nil {
		return "", err
	}
	claimsJSON, err := json.Marshal(claims)
	if err != nil {
		return "", err
	}
	encodedHeader := base64.RawURLEncoding.EncodeToString(headerJSON)
	encodedClaims := base64.RawURLEncoding.EncodeToString(claimsJSON)
	signingInput := encodedHeader + "." + encodedClaims
	signature := ed25519.Sign(privateKey, []byte(signingInput))
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(signature), nil
}

func parseJWT(token string) (protectedHeader, []byte, []byte, string, string, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return protectedHeader{}, nil, nil, "", "", ErrInvalidToken
	}
	headerJSON, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return protectedHeader{}, nil, nil, "", "", ErrInvalidToken
	}
	payloadJSON, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return protectedHeader{}, nil, nil, "", "", ErrInvalidToken
	}
	signature, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return protectedHeader{}, nil, nil, "", "", ErrInvalidToken
	}
	var header protectedHeader
	if err := json.Unmarshal(headerJSON, &header); err != nil {
		return protectedHeader{}, nil, nil, "", "", ErrInvalidToken
	}
	if header.Type != "JWT" || header.Alg != "EdDSA" || header.KeyID == "" {
		return protectedHeader{}, nil, nil, "", "", ErrInvalidToken
	}
	sum := sha256.Sum256([]byte(token))
	return header, payloadJSON, signature, parts[0] + "." + parts[1], hex.EncodeToString(sum[:]), nil
}

func unverifiedIssuer(token string) (string, error) {
	_, payloadJSON, _, _, _, err := parseJWT(token)
	if err != nil {
		return "", err
	}
	var claims struct {
		Issuer string `json:"iss"`
	}
	if err := json.Unmarshal(payloadJSON, &claims); err != nil {
		return "", ErrInvalidToken
	}
	if claims.Issuer == "" {
		return "", ErrUntrustedIssuer
	}
	return claims.Issuer, nil
}

func verifySignature(publicKey ed25519.PublicKey, signingInput string, signature []byte) error {
	if len(publicKey) != ed25519.PublicKeySize || !ed25519.Verify(publicKey, []byte(signingInput), signature) {
		return ErrInvalidToken
	}
	return nil
}

func SignCapability(keys *KeySet, claims CapabilityClaims) (string, error) {
	kid, privateKey, err := keys.ActivePrivateKey()
	if err != nil {
		return "", err
	}
	return signJWT(privateKey, kid, "capability", claims)
}

func SignApproval(keys *KeySet, claims ApprovalClaims) (string, error) {
	kid, privateKey, err := keys.ActivePrivateKey()
	if err != nil {
		return "", err
	}
	return signJWT(privateKey, kid, "approval", claims)
}

func (k *KeySet) VerifyCapability(token string, now time.Time) (VerifiedCapability, error) {
	header, payloadJSON, signature, signingInput, tokenHash, err := parseJWT(token)
	if err != nil {
		return VerifiedCapability{}, err
	}
	if header.TokenKind != "" && header.TokenKind != "capability" {
		return VerifiedCapability{}, ErrInvalidToken
	}
	key, err := k.PublicKey(header.KeyID, now)
	if err != nil {
		return VerifiedCapability{}, err
	}
	if err := verifySignature(key, signingInput, signature); err != nil {
		return VerifiedCapability{}, err
	}
	var claims CapabilityClaims
	if err := json.Unmarshal(payloadJSON, &claims); err != nil {
		return VerifiedCapability{}, ErrInvalidToken
	}
	return VerifiedCapability{
		Header:     header,
		Claims:     claims,
		SigningKey: header.KeyID,
		TokenHash:  tokenHash,
	}, nil
}

func (k *KeySet) VerifyApproval(token string, now time.Time) (VerifiedApproval, error) {
	header, payloadJSON, signature, signingInput, tokenHash, err := parseJWT(token)
	if err != nil {
		return VerifiedApproval{}, err
	}
	if header.TokenKind != "" && header.TokenKind != "approval" {
		return VerifiedApproval{}, ErrInvalidToken
	}
	key, err := k.PublicKey(header.KeyID, now)
	if err != nil {
		return VerifiedApproval{}, err
	}
	if err := verifySignature(key, signingInput, signature); err != nil {
		return VerifiedApproval{}, err
	}
	var claims ApprovalClaims
	if err := json.Unmarshal(payloadJSON, &claims); err != nil {
		return VerifiedApproval{}, ErrInvalidToken
	}
	return VerifiedApproval{
		Header:     header,
		Claims:     claims,
		SigningKey: header.KeyID,
		TokenHash:  tokenHash,
	}, nil
}

func tokenHash(token string) string {
	sum := sha256.Sum256([]byte(token))
	return fmt.Sprintf("%x", sum[:])
}
