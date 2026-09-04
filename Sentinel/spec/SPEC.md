# Sentinel audit-chain portable profile

**Version:** `sentinel.audit.v1-portable`

This specification defines the portable subset of Sentinel's JSON Lines audit
format and the verification algorithm implemented independently in Python,
TypeScript, and Go. It is designed for audit records that must be checked
without trusting the process or programming language that wrote them.

This document is a technical specification, not a security certification. A
hash chain makes alteration of retained records detectable; it does not prevent
host compromise, key theft, deletion of the entire file, or truncation of the
tail.

## 1. Record envelope

Each UTF-8 line is one JSON object with exactly these fields:

| Field | Type | Meaning |
|---|---|---|
| `sequence` | safe integer | One-based contiguous record number |
| `timestamp` | string | UTC timestamp recorded by the writer |
| `agent` | string | Logical actor proposing the action |
| `action` | string | Action name |
| `target` | string | Action target |
| `allowed` | boolean | Policy decision |
| `reason` | string | Human-reviewable decision rationale |
| `payload` | object | Bounded action metadata |
| `keyed` | boolean | `true` for HMAC-SHA256, otherwise SHA-256 |
| `previous_hash` | string | Lowercase hexadecimal digest of prior record |
| `hash` | string | Lowercase hexadecimal digest of this record |

The first record's `previous_hash` is 64 zero characters. Every subsequent
record's `previous_hash` must equal the preceding record's `hash`.

## 2. Portable JSON value profile

The portable profile permits:

- `null`;
- booleans;
- strings;
- arrays;
- objects whose keys are strings; and
- integers from `-9007199254740991` through `9007199254740991`.

Floating-point values, exponent notation, `NaN`, and infinities are outside the
portable profile. The range is intentionally the IEEE-754 safe-integer range so
all three reference implementations can represent values without precision
loss.

Object keys are compared by Unicode code point for sorting. The supplied
record schema uses ASCII field names. Implementations must reject duplicate
JSON object keys before digest verification where their parser can expose that
condition.

## 3. Canonical serialization

To compute a record digest:

1. Parse the line as JSON.
2. Remove the top-level `hash` field.
3. Serialize the remaining value recursively:
   - object keys are sorted in ascending lexical order;
   - arrays retain their original order;
   - no insignificant whitespace is emitted;
   - strings use JSON escapes for quotes, reverse solidus, and control
     characters;
   - every non-ASCII UTF-16 code unit is emitted as lowercase `\uXXXX`;
   - safe integers are emitted in base 10 with no leading plus sign or leading
     zeroes, except the value zero itself; and
   - `true`, `false`, and `null` use those exact lowercase tokens.
4. Encode the resulting canonical JSON string as UTF-8.

This is the behavior of Python's `json.dumps(value, sort_keys=True,
separators=(",", ":"), ensure_ascii=True)` for values inside the portable
profile.

## 4. Digest modes

### Unkeyed

When `keyed` is `false`, the record digest is:

```text
SHA-256(canonical_record_bytes)
```

An unkeyed chain detects accidental corruption and untrusted modification only
when the attacker cannot rewrite the entire chain without detection elsewhere.
It does not authenticate the writer.

### Keyed

When `keyed` is `true`, the record digest is:

```text
HMAC-SHA256(key, canonical_record_bytes)
```

The key must be supplied out of band. It must not be stored in the audit file.
The fixture key `sentinel-demo-key` is public test data and must never be used
in a deployment.

## 5. Verification algorithm

Given an optional key and a JSONL stream:

1. Set `expected_sequence = 1`.
2. Set `expected_previous_hash = "0" * 64`.
3. For every nonblank line:
   1. Parse and validate the record.
   2. Require `sequence == expected_sequence`.
   3. Require `previous_hash == expected_previous_hash`.
   4. If a key was supplied, require `keyed == true`.
   5. If no key was supplied, require `keyed == false`.
   6. Recompute the digest in the declared mode.
   7. Compare the recomputed digest with `hash` using a constant-time
      comparison.
   8. Set `expected_previous_hash = hash` and increment the sequence.
4. Return the record count and final digest.

A verifier holding a key must reject any unkeyed record. This prevents an
attacker from flipping `keyed` to `false`, recomputing a plain SHA-256 chain,
and asking a keyed verifier to accept the downgrade.

A valid file may not mix keyed and unkeyed records.

## 6. Failure behavior

Verification fails closed on the first:

- malformed JSON line;
- missing or extra envelope field;
- unsupported JSON value;
- unsafe integer;
- invalid digest encoding;
- sequence gap;
- chain-link mismatch;
- keyed/unkeyed mode mismatch; or
- content digest mismatch.

Errors identify the line or sequence without printing secret key material.

## 7. Conformance vectors

`vectors/unkeyed.jsonl` and `vectors/keyed.jsonl` are normative examples for
this profile. `vectors/manifest.json` records the expected record count and
final digest. The keyed fixture uses the public key `sentinel-demo-key`.

A conforming verifier must:

- accept both vectors in the appropriate mode;
- reject the keyed vector without a key;
- reject the unkeyed vector when a key is supplied;
- reject a changed field;
- reject a deleted or reordered middle record; and
- reject a keyed-to-unkeyed downgrade.

## 8. Production boundary

The format does not establish completeness of the log. To detect deletion of
the complete file or truncation of its tail, periodically anchor the final
digest outside the writing host—for example in object-lock storage, a
transparency log, or another independently controlled system.

Keep the HMAC key in a secrets manager or HSM, use least-privilege access,
rotate it with an explicit chain boundary, and preserve the exact policy
fingerprint associated with every run.
