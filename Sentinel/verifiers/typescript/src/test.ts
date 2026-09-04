interface RequireFunction {
  (id: string): unknown;
}

declare const require: RequireFunction;
declare const __dirname: string;

interface FileSystem {
  readFileSync(path: string, encoding: "utf8"): string;
  writeFileSync(path: string, value: string, encoding: "utf8"): void;
  mkdtempSync(prefix: string): string;
}

interface PathModule {
  resolve(...parts: string[]): string;
  join(...parts: string[]): string;
}

interface OsModule {
  tmpdir(): string;
}

const fs = require("node:fs") as FileSystem;
const path = require("node:path") as PathModule;
const os = require("node:os") as OsModule;

import { VerificationError, verifyFile } from "./verifier";

const vectors = path.resolve(__dirname, "../../../spec/vectors");

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function expectVerificationError(operation: () => void, text: string): void {
  try {
    operation();
  } catch (error) {
    if (!(error instanceof VerificationError)) {
      throw new Error("expected VerificationError");
    }
    assert(error.message.includes(text), `expected error containing ${text}`);
    return;
  }
  throw new Error("expected verification to fail");
}

function testVectors(): void {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(vectors, "manifest.json"), "utf8"),
  ) as { files: Record<string, { records: number; final_hash: string }> };

  const unkeyed = verifyFile(path.join(vectors, "unkeyed.jsonl"));
  assert(unkeyed.records === 3, "unkeyed record count mismatch");
  assert(
    unkeyed.finalHash === manifest.files["unkeyed.jsonl"].final_hash,
    "unkeyed final hash mismatch",
  );

  const keyed = verifyFile(path.join(vectors, "keyed.jsonl"), "sentinel-demo-key");
  assert(keyed.records === 3, "keyed record count mismatch");
  assert(
    keyed.finalHash === manifest.files["keyed.jsonl"].final_hash,
    "keyed final hash mismatch",
  );
}

function testModeFailures(): void {
  expectVerificationError(
    () => verifyFile(path.join(vectors, "keyed.jsonl")),
    "requires a key",
  );
  expectVerificationError(
    () => verifyFile(path.join(vectors, "unkeyed.jsonl"), "sentinel-demo-key"),
    "refused downgrade",
  );
}

function testTampering(): void {
  const lines = fs
    .readFileSync(path.join(vectors, "unkeyed.jsonl"), "utf8")
    .trim()
    .split("\n");
  const record = JSON.parse(lines[1]) as Record<string, unknown>;
  record.reason = "rewritten after approval";
  lines[1] = JSON.stringify(record);
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "sentinel-ts-"));
  const tampered = path.join(directory, "tampered.jsonl");
  fs.writeFileSync(tampered, `${lines.join("\n")}\n`, "utf8");
  expectVerificationError(() => verifyFile(tampered), "content digest mismatch");
}

function main(): void {
  testVectors();
  testModeFailures();
  testTampering();
  console.log("TypeScript conformance tests passed");
}

main();
