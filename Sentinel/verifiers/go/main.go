// Command sentinel-audit-verify independently verifies the
// sentinel.audit.v1-portable JSONL audit-chain profile.
package main

import (
	"bufio"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf16"
)

const (
	genesisHash = "0000000000000000000000000000000000000000000000000000000000000000"
	safeInteger = int64(9_007_199_254_740_991)
)

var (
	hashPattern    = regexp.MustCompile(`^[0-9a-f]{64}$`)
	integerPattern = regexp.MustCompile(`^-?(0|[1-9][0-9]*)$`)
	recordFields   = []string{
		"action",
		"agent",
		"allowed",
		"hash",
		"keyed",
		"payload",
		"previous_hash",
		"reason",
		"sequence",
		"target",
		"timestamp",
	}
)

// VerificationError describes the first portable-profile or chain violation.
type VerificationError struct {
	Message string
}

func (e *VerificationError) Error() string { return e.Message }

// VerificationResult reports the number of verified records and final digest.
type VerificationResult struct {
	Records   int
	FinalHash string
}

func fail(format string, arguments ...any) error {
	return &VerificationError{Message: fmt.Sprintf(format, arguments...)}
}

func decodeRecord(raw string, lineNumber int) (map[string]any, error) {
	decoder := json.NewDecoder(strings.NewReader(raw))
	decoder.UseNumber()

	var value any
	if err := decoder.Decode(&value); err != nil {
		return nil, fail("line %d: malformed JSON: %v", lineNumber, err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return nil, fail("line %d: multiple JSON values", lineNumber)
		}
		return nil, fail("line %d: trailing JSON data: %v", lineNumber, err)
	}

	record, ok := value.(map[string]any)
	if !ok {
		return nil, fail("line %d: record must be an object", lineNumber)
	}
	keys := make([]string, 0, len(record))
	for key := range record {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	if len(keys) != len(recordFields) {
		return nil, fail("line %d: envelope fields do not match spec", lineNumber)
	}
	for index, key := range keys {
		if key != recordFields[index] {
			return nil, fail("line %d: envelope fields do not match spec", lineNumber)
		}
	}
	if err := validateValue(record, "$"); err != nil {
		return nil, fail("line %d: %v", lineNumber, err)
	}
	return record, nil
}

func validateValue(value any, path string) error {
	switch typed := value.(type) {
	case nil, bool, string:
		return nil
	case json.Number:
		text := typed.String()
		if !integerPattern.MatchString(text) {
			return fail("%s: number must be a portable safe integer", path)
		}
		integer, err := strconv.ParseInt(text, 10, 64)
		if err != nil || integer < -safeInteger || integer > safeInteger {
			return fail("%s: integer exceeds portable safe range", path)
		}
		return nil
	case []any:
		for index, item := range typed {
			if err := validateValue(item, fmt.Sprintf("%s[%d]", path, index)); err != nil {
				return err
			}
		}
		return nil
	case map[string]any:
		for key, item := range typed {
			if err := validateValue(item, path+"."+key); err != nil {
				return err
			}
		}
		return nil
	default:
		return fail("%s: unsupported JSON value %T", path, value)
	}
}

func encodePythonString(builder *strings.Builder, value string) {
	builder.WriteByte('"')
	for _, codeUnit := range utf16.Encode([]rune(value)) {
		switch codeUnit {
		case '\b':
			builder.WriteString(`\b`)
		case '\t':
			builder.WriteString(`\t`)
		case '\n':
			builder.WriteString(`\n`)
		case '\f':
			builder.WriteString(`\f`)
		case '\r':
			builder.WriteString(`\r`)
		case '"':
			builder.WriteString(`\"`)
		case '\\':
			builder.WriteString(`\\`)
		default:
			if codeUnit < 0x20 || codeUnit > 0x7e {
				fmt.Fprintf(builder, `\u%04x`, codeUnit)
			} else {
				builder.WriteRune(rune(codeUnit))
			}
		}
	}
	builder.WriteByte('"')
}

func writeCanonical(builder *strings.Builder, value any) error {
	switch typed := value.(type) {
	case nil:
		builder.WriteString("null")
	case bool:
		if typed {
			builder.WriteString("true")
		} else {
			builder.WriteString("false")
		}
	case string:
		encodePythonString(builder, typed)
	case json.Number:
		if err := validateValue(typed, "$"); err != nil {
			return err
		}
		builder.WriteString(typed.String())
	case []any:
		builder.WriteByte('[')
		for index, item := range typed {
			if index > 0 {
				builder.WriteByte(',')
			}
			if err := writeCanonical(builder, item); err != nil {
				return err
			}
		}
		builder.WriteByte(']')
	case map[string]any:
		keys := make([]string, 0, len(typed))
		for key := range typed {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		builder.WriteByte('{')
		for index, key := range keys {
			if index > 0 {
				builder.WriteByte(',')
			}
			encodePythonString(builder, key)
			builder.WriteByte(':')
			if err := writeCanonical(builder, typed[key]); err != nil {
				return err
			}
		}
		builder.WriteByte('}')
	default:
		return fail("unsupported canonical JSON value %T", value)
	}
	return nil
}

func canonicalBytes(record map[string]any) ([]byte, error) {
	body := make(map[string]any, len(record)-1)
	for key, value := range record {
		if key != "hash" {
			body[key] = value
		}
	}
	var builder strings.Builder
	if err := writeCanonical(&builder, body); err != nil {
		return nil, err
	}
	return []byte(builder.String()), nil
}

func expectedDigest(record map[string]any, key []byte) (string, error) {
	canonical, err := canonicalBytes(record)
	if err != nil {
		return "", err
	}
	if key == nil {
		digest := sha256.Sum256(canonical)
		return hex.EncodeToString(digest[:]), nil
	}
	mac := hmac.New(sha256.New, key)
	_, _ = mac.Write(canonical)
	return hex.EncodeToString(mac.Sum(nil)), nil
}

func typedString(record map[string]any, name string, lineNumber int) (string, error) {
	value, ok := record[name].(string)
	if !ok {
		return "", fail("line %d: %s must be a string", lineNumber, name)
	}
	return value, nil
}

func typedBool(record map[string]any, name string, lineNumber int) (bool, error) {
	value, ok := record[name].(bool)
	if !ok {
		return false, fail("line %d: %s must be a boolean", lineNumber, name)
	}
	return value, nil
}

func typedSafeInteger(record map[string]any, name string, lineNumber int) (int64, error) {
	value, ok := record[name].(json.Number)
	if !ok || !integerPattern.MatchString(value.String()) {
		return 0, fail("line %d: %s must be a safe integer", lineNumber, name)
	}
	integer, err := strconv.ParseInt(value.String(), 10, 64)
	if err != nil || integer < -safeInteger || integer > safeInteger {
		return 0, fail("line %d: %s exceeds the safe-integer range", lineNumber, name)
	}
	return integer, nil
}

// Verify reads and validates a portable audit-chain stream.
func Verify(reader io.Reader, key []byte) (VerificationResult, error) {
	scanner := bufio.NewScanner(reader)
	scanner.Buffer(make([]byte, 64*1024), 2*1024*1024)

	expectedSequence := int64(1)
	expectedPrevious := genesisHash
	count := 0
	lineNumber := 0

	for scanner.Scan() {
		lineNumber++
		raw := scanner.Text()
		if strings.TrimSpace(raw) == "" {
			continue
		}
		record, err := decodeRecord(raw, lineNumber)
		if err != nil {
			return VerificationResult{}, err
		}

		sequence, err := typedSafeInteger(record, "sequence", lineNumber)
		if err != nil {
			return VerificationResult{}, err
		}
		if sequence != expectedSequence {
			return VerificationResult{}, fail(
				"line %d: expected sequence %d, got %d",
				lineNumber,
				expectedSequence,
				sequence,
			)
		}

		previous, err := typedString(record, "previous_hash", lineNumber)
		if err != nil {
			return VerificationResult{}, err
		}
		digest, err := typedString(record, "hash", lineNumber)
		if err != nil {
			return VerificationResult{}, err
		}
		if !hashPattern.MatchString(previous) {
			return VerificationResult{}, fail("line %d: invalid previous_hash", lineNumber)
		}
		if !hashPattern.MatchString(digest) {
			return VerificationResult{}, fail("line %d: invalid hash", lineNumber)
		}
		if previous != expectedPrevious {
			return VerificationResult{}, fail("line %d: previous_hash mismatch", lineNumber)
		}

		keyed, err := typedBool(record, "keyed", lineNumber)
		if err != nil {
			return VerificationResult{}, err
		}
		if key != nil && !keyed {
			return VerificationResult{}, fail(
				"line %d: keyed verifier refused downgrade",
				lineNumber,
			)
		}
		if key == nil && keyed {
			return VerificationResult{}, fail("line %d: keyed record requires a key", lineNumber)
		}

		calculated, err := expectedDigest(record, key)
		if err != nil {
			return VerificationResult{}, fail("line %d: %v", lineNumber, err)
		}
		if !hmac.Equal([]byte(calculated), []byte(digest)) {
			return VerificationResult{}, fail("line %d: content digest mismatch", lineNumber)
		}

		count++
		expectedSequence++
		expectedPrevious = digest
	}
	if err := scanner.Err(); err != nil {
		return VerificationResult{}, err
	}
	return VerificationResult{Records: count, FinalHash: expectedPrevious}, nil
}

// VerifyFile verifies a portable audit-chain file from disk.
func VerifyFile(path string, key []byte) (VerificationResult, error) {
	handle, err := os.Open(path)
	if err != nil {
		return VerificationResult{}, err
	}
	defer handle.Close()
	return Verify(handle, key)
}

func run(arguments []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("sentinel-audit-verify", flag.ContinueOnError)
	flags.SetOutput(stderr)
	logPath := flags.String("log", "", "audit JSONL path")
	keyText := flags.String("key", "", "HMAC fixture/deployment key")
	if err := flags.Parse(arguments); err != nil {
		return 2
	}
	if *logPath == "" {
		fmt.Fprintln(stderr, "INVALID: --log is required")
		return 2
	}
	var key []byte
	if *keyText != "" {
		key = []byte(*keyText)
	}
	result, err := VerifyFile(*logPath, key)
	if err != nil {
		fmt.Fprintf(stderr, "INVALID: %v\n", err)
		return 1
	}
	fmt.Fprintf(stdout, "OK records=%d final_hash=%s\n", result.Records, result.FinalHash)
	return 0
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}
