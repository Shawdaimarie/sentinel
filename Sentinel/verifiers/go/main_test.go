package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func vectorPath(name string) string {
	return filepath.Join("..", "..", "spec", "vectors", name)
}

func TestAcceptsReferenceVectors(t *testing.T) {
	manifestBytes, err := os.ReadFile(vectorPath("manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest struct {
		Files map[string]struct {
			Records   int    `json:"records"`
			FinalHash string `json:"final_hash"`
		} `json:"files"`
	}
	if err := json.Unmarshal(manifestBytes, &manifest); err != nil {
		t.Fatal(err)
	}

	unkeyed, err := VerifyFile(vectorPath("unkeyed.jsonl"), nil)
	if err != nil {
		t.Fatal(err)
	}
	if unkeyed.Records != manifest.Files["unkeyed.jsonl"].Records ||
		unkeyed.FinalHash != manifest.Files["unkeyed.jsonl"].FinalHash {
		t.Fatalf("unkeyed result mismatch: %+v", unkeyed)
	}

	keyed, err := VerifyFile(vectorPath("keyed.jsonl"), []byte("sentinel-demo-key"))
	if err != nil {
		t.Fatal(err)
	}
	if keyed.Records != manifest.Files["keyed.jsonl"].Records ||
		keyed.FinalHash != manifest.Files["keyed.jsonl"].FinalHash {
		t.Fatalf("keyed result mismatch: %+v", keyed)
	}
}

func expectFailure(t *testing.T, operation func() error, contains string) {
	t.Helper()
	err := operation()
	if err == nil {
		t.Fatal("expected verification failure")
	}
	if !strings.Contains(err.Error(), contains) {
		t.Fatalf("expected %q in %q", contains, err.Error())
	}
}

func TestModeFailures(t *testing.T) {
	expectFailure(t, func() error {
		_, err := VerifyFile(vectorPath("keyed.jsonl"), nil)
		return err
	}, "requires a key")

	expectFailure(t, func() error {
		_, err := VerifyFile(vectorPath("unkeyed.jsonl"), []byte("sentinel-demo-key"))
		return err
	}, "refused downgrade")
}

func TestChangedRecordIsRejected(t *testing.T) {
	content, err := os.ReadFile(vectorPath("unkeyed.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	var record map[string]any
	decoder := json.NewDecoder(strings.NewReader(lines[1]))
	decoder.UseNumber()
	if err := decoder.Decode(&record); err != nil {
		t.Fatal(err)
	}
	record["reason"] = "rewritten after approval"
	changed, err := json.Marshal(record)
	if err != nil {
		t.Fatal(err)
	}
	lines[1] = string(changed)

	expectFailure(t, func() error {
		_, err := Verify(strings.NewReader(strings.Join(lines, "\n")+"\n"), nil)
		return err
	}, "content digest mismatch")
}

func TestDeletedMiddleRecordIsRejected(t *testing.T) {
	content, err := os.ReadFile(vectorPath("unkeyed.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	deleted := strings.Join([]string{lines[0], lines[2]}, "\n") + "\n"

	expectFailure(t, func() error {
		_, err := Verify(strings.NewReader(deleted), nil)
		return err
	}, "expected sequence 2")
}

func TestPythonCompatibleUnicodeCanonicalization(t *testing.T) {
	result, err := VerifyFile(vectorPath("keyed.jsonl"), []byte("sentinel-demo-key"))
	if err != nil {
		t.Fatal(err)
	}
	if result.FinalHash != "8409da90cd06f8bae23c4baf4008132b4d9c0f89464e58873889a12e43282901" {
		t.Fatalf("unexpected keyed final hash: %s", result.FinalHash)
	}
}

func TestCLI(t *testing.T) {
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	status := run(
		[]string{"--log", vectorPath("unkeyed.jsonl")},
		&stdout,
		&stderr,
	)
	if status != 0 {
		t.Fatalf("status=%d stderr=%s", status, stderr.String())
	}
	if !strings.Contains(stdout.String(), "OK records=3") {
		t.Fatalf("unexpected stdout: %s", stdout.String())
	}
}
