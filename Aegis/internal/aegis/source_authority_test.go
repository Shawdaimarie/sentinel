package aegis

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"testing"
)

func TestPolicyHashDoesNotMutateHumanPolicy(t *testing.T) {
	p := Policy{Rules: []Rule{{ID: "r", Subjects: []string{"z", "a"}, Tools: []string{"z", "a"}}}}
	expected := []string{"z", "a"}
	var workers sync.WaitGroup
	for i := 0; i < 20; i++ {
		workers.Add(1)
		go func() { defer workers.Done(); _ = p.Hash() }()
	}
	workers.Wait()
	if !reflect.DeepEqual(p.Rules[0].Subjects, expected) || !reflect.DeepEqual(p.Rules[0].Tools, expected) {
		t.Fatal("hash calculation mutated the operator's policy")
	}
}

func TestPolicyRejectsMisspelledApprovalField(t *testing.T) {
	path := filepath.Join(t.TempDir(), "policy.json")
	if err := os.WriteFile(path, []byte(`{"rules":[{"id":"write","effect":"allow","require_approvals":true}]}`), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadPolicy(path); err == nil {
		t.Fatal("unknown approval field must not silently disable human approval")
	}
}

func TestGatewayRejectsTrailingJSONBeforeAuthorization(t *testing.T) {
	authorizer, _, _, _ := testAuthorizer(t)
	handler := HTTPHandler{Authorizer: authorizer}
	for _, body := range []string{`{} {"approval_token":"forged"}`, `{} junk`} {
		req := httptest.NewRequest(http.MethodPost, "/v1/authorize", strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()
		handler.authorize(rec, req)
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("expected rejection of trailing input, got %d", rec.Code)
		}
	}
}
