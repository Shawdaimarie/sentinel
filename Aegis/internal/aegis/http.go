package aegis

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"time"
)

const maxAuthorizationBodyBytes = 64 * 1024

type HTTPConfig struct {
	Issuer      string
	ListenAddr  string
	JWKSPath    string
	ServiceName string
}

type HTTPHandler struct {
	Authorizer *Authorizer
	Config     HTTPConfig
}

func NewHTTPServer(handler HTTPHandler) *http.Server {
	addr := handler.Config.ListenAddr
	if addr == "" {
		addr = "127.0.0.1:8080"
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/.well-known/openid-configuration", handler.openIDConfiguration)
	mux.HandleFunc("/jwks.json", handler.jwks)
	mux.HandleFunc("/v1/authorize", handler.authorize)
	return &http.Server{
		Addr:              addr,
		Handler:           mux,
		ReadHeaderTimeout: 3 * time.Second,
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      5 * time.Second,
		IdleTimeout:       30 * time.Second,
		MaxHeaderBytes:    16 * 1024,
	}
}

func (h HTTPHandler) openIDConfiguration(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	issuer := h.Config.Issuer
	if issuer == "" && h.Authorizer != nil {
		issuer = h.Authorizer.Policy.Issuer
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"issuer":                                issuer,
		"jwks_uri":                              strings.TrimRight(issuer, "/") + "/jwks.json",
		"id_token_signing_alg_values_supported": []string{"EdDSA"},
		"subject_types_supported":               []string{"public"},
	})
}

func (h HTTPHandler) jwks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if h.Authorizer == nil || h.Authorizer.Keys == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "configuration_unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, h.Authorizer.Keys.PublicJWKS())
}

func (h HTTPHandler) authorize(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	contentType := r.Header.Get("Content-Type")
	if contentType == "" || !strings.HasPrefix(contentType, "application/json") {
		writeJSON(w, http.StatusUnsupportedMediaType, map[string]string{"error": "content_type_required"})
		return
	}
	if h.Authorizer == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "configuration_unavailable"})
		return
	}
	defer r.Body.Close()
	limitedBody := http.MaxBytesReader(w, r.Body, maxAuthorizationBodyBytes)
	decoder := json.NewDecoder(limitedBody)
	decoder.DisallowUnknownFields()
	var request AuthorizationRequest
	if err := decoder.Decode(&request); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid_json"})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	request.TraceParent = r.Header.Get("Traceparent")
	result := h.Authorizer.Authorize(ctx, request)
	status := http.StatusForbidden
	if result.Allowed {
		status = http.StatusOK
	}
	writeJSON(w, status, result)
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(append(data, '\n'))
}
