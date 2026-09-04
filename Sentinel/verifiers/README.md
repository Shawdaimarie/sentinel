# Independent portable audit verifiers

This directory contains three independently implemented verifiers for the
[`sentinel.audit.v1-portable`](../spec/SPEC.md) audit-chain profile.

| Implementation | Runtime dependencies | Test command |
|---|---|---|
| Python | Standard library only | `python -m unittest discover -s verifiers/python -p "test_*.py" -v` |
| TypeScript | Node standard library after compilation | `cd verifiers/typescript && tsc -p tsconfig.json && node dist/test.js` |
| Go | Standard library only | `cd verifiers/go && go test ./...` |

All implementations verify the same normative keyed and unkeyed vectors under
[`spec/vectors/`](../spec/vectors/). CI requires identical record counts and
final digests and exercises tampering, deletion, key-mode mismatch, and
keyed-to-unkeyed downgrade failures.

## CLI examples

From the `Sentinel/` directory:

```bash
python verifiers/python/verify.py \
  --log spec/vectors/unkeyed.jsonl

cd verifiers/typescript
tsc -p tsconfig.json
node dist/verifier.js --log ../../spec/vectors/unkeyed.jsonl

cd ../go
go run . --log ../../spec/vectors/unkeyed.jsonl
```

For the keyed fixture, add `--key sentinel-demo-key`. That key is public test
data and must never be used in a deployment.

## Trust boundary

Independent implementations reduce language/runtime coupling; they do not make
the writing host trustworthy. Production systems should keep the HMAC key
outside the writer, anchor final digests externally, and independently control
the storage used to establish log completeness.
