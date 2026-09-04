/* Independent TypeScript verifier for sentinel.audit.v1-portable. */

interface RequireFunction {
  (id: string): unknown;
  main: unknown;
}

declare const require: RequireFunction;
declare const module: unknown;
declare const process: {
  argv: string[];
  stderr: { write(value: string): void };
  stdout: { write(value: string): void };
  exitCode?: number;
};

interface FileSystem {
  readFileSync(path: string, encoding: "utf8"): string;
}

interface HashLike {
  update(value: string, encoding: "utf8"): HashLike;
  digest(encoding: "hex"): string;
}

interface CryptoModule {
  createHash(algorithm: "sha256"): HashLike;
  createHmac(algorithm: "sha256", key: string): HashLike;
}

const fs = require("node:fs") as FileSystem;
const crypto = require("node:crypto") as CryptoModule;

const GENESIS_HASH = "0".repeat(64);
const HASH_RE = /^[0-9a-f]{64}$/;
const SAFE_INTEGER = 9_007_199_254_740_991;
const FIELDS = [
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
] as const;

type JsonValue = null | boolean | string | number | JsonValue[] | JsonObject;
type JsonObject = { [key: string]: JsonValue };

export class VerificationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "VerificationError";
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validateValue(value: unknown, path = "$"): asserts value is JsonValue {
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    return;
  }
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || Math.abs(value) > SAFE_INTEGER) {
      throw new VerificationError(`${path}: number must be a portable safe integer`);
    }
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => validateValue(item, `${path}[${index}]`));
    return;
  }
  if (isObject(value)) {
    for (const [key, item] of Object.entries(value)) {
      validateValue(item, `${path}.${key}`);
    }
    return;
  }
  throw new VerificationError(`${path}: unsupported JSON value`);
}

function compareCodePoints(left: string, right: string): number {
  const a = Array.from(left, (character) => character.codePointAt(0) ?? 0);
  const b = Array.from(right, (character) => character.codePointAt(0) ?? 0);
  const length = Math.min(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    if (a[index] !== b[index]) {
      return a[index] < b[index] ? -1 : 1;
    }
  }
  return a.length - b.length;
}

function encodeString(value: string): string {
  let encoded = '"';
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    switch (code) {
      case 0x08:
        encoded += "\\b";
        break;
      case 0x09:
        encoded += "\\t";
        break;
      case 0x0a:
        encoded += "\\n";
        break;
      case 0x0c:
        encoded += "\\f";
        break;
      case 0x0d:
        encoded += "\\r";
        break;
      case 0x22:
        encoded += '\\"';
        break;
      case 0x5c:
        encoded += "\\\\";
        break;
      default:
        if (code < 0x20 || code > 0x7e) {
          encoded += `\\u${code.toString(16).padStart(4, "0")}`;
        } else {
          encoded += value[index];
        }
    }
  }
  return `${encoded}"`;
}

export function canonicalJson(value: JsonValue): string {
  if (value === null) {
    return "null";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) {
      throw new VerificationError("canonical JSON only permits safe integers");
    }
    return String(value);
  }
  if (typeof value === "string") {
    return encodeString(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  }
  const members = Object.keys(value)
    .sort(compareCodePoints)
    .map((key) => `${encodeString(key)}:${canonicalJson(value[key])}`);
  return `{${members.join(",")}}`;
}

function parseRecord(raw: string, lineNumber: number): JsonObject {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw) as unknown;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "unknown parse error";
    throw new VerificationError(`line ${lineNumber}: malformed JSON: ${detail}`);
  }
  if (!isObject(parsed)) {
    throw new VerificationError(`line ${lineNumber}: record must be an object`);
  }
  const keys = Object.keys(parsed).sort(compareCodePoints);
  if (keys.length !== FIELDS.length || keys.some((key, index) => key !== FIELDS[index])) {
    throw new VerificationError(`line ${lineNumber}: envelope fields do not match spec`);
  }
  validateValue(parsed);
  return parsed as JsonObject;
}

function safeEqual(left: string, right: string): boolean {
  if (left.length !== right.length) {
    return false;
  }
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function computeDigest(record: JsonObject, key?: string): string {
  const body: JsonObject = {};
  for (const [name, value] of Object.entries(record)) {
    if (name !== "hash") {
      body[name] = value;
    }
  }
  const canonical = canonicalJson(body);
  return key === undefined
    ? crypto.createHash("sha256").update(canonical, "utf8").digest("hex")
    : crypto.createHmac("sha256", key).update(canonical, "utf8").digest("hex");
}

export interface VerificationResult {
  records: number;
  finalHash: string;
}

export function verifyText(text: string, key?: string): VerificationResult {
  let expectedSequence = 1;
  let expectedPrevious = GENESIS_HASH;
  let count = 0;

  const lines = text.split(/\r?\n/);
  lines.forEach((raw, index) => {
    if (raw.trim() === "") {
      return;
    }
    const lineNumber = index + 1;
    const record = parseRecord(raw, lineNumber);

    if (record.sequence !== expectedSequence) {
      throw new VerificationError(
        `line ${lineNumber}: expected sequence ${expectedSequence}, got ${String(record.sequence)}`,
      );
    }
    if (typeof record.previous_hash !== "string" || !HASH_RE.test(record.previous_hash)) {
      throw new VerificationError(`line ${lineNumber}: invalid previous_hash`);
    }
    if (typeof record.hash !== "string" || !HASH_RE.test(record.hash)) {
      throw new VerificationError(`line ${lineNumber}: invalid hash`);
    }
    if (record.previous_hash !== expectedPrevious) {
      throw new VerificationError(`line ${lineNumber}: previous_hash mismatch`);
    }
    if (typeof record.keyed !== "boolean") {
      throw new VerificationError(`line ${lineNumber}: keyed must be a boolean`);
    }
    if (key !== undefined && !record.keyed) {
      throw new VerificationError(`line ${lineNumber}: keyed verifier refused downgrade`);
    }
    if (key === undefined && record.keyed) {
      throw new VerificationError(`line ${lineNumber}: keyed record requires a key`);
    }

    const calculated = computeDigest(record, key);
    if (!safeEqual(calculated, record.hash)) {
      throw new VerificationError(`line ${lineNumber}: content digest mismatch`);
    }

    count += 1;
    expectedSequence += 1;
    expectedPrevious = record.hash;
  });

  return { records: count, finalHash: expectedPrevious };
}

export function verifyFile(path: string, key?: string): VerificationResult {
  return verifyText(fs.readFileSync(path, "utf8"), key);
}

function parseArguments(argv: string[]): { log: string; key?: string } {
  let log: string | undefined;
  let key: string | undefined;
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--log") {
      log = argv[index + 1];
      index += 1;
    } else if (value === "--key") {
      key = argv[index + 1];
      index += 1;
    } else {
      throw new VerificationError(`unknown argument: ${value}`);
    }
  }
  if (!log) {
    throw new VerificationError("--log is required");
  }
  return key === undefined ? { log } : { log, key };
}

function main(): void {
  try {
    const args = parseArguments(process.argv.slice(2));
    const result = verifyFile(args.log, args.key);
    process.stdout.write(`OK records=${result.records} final_hash=${result.finalHash}\n`);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    process.stderr.write(`INVALID: ${detail}\n`);
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main();
}
