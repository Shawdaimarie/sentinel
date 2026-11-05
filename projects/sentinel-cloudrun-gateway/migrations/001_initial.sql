CREATE TABLE IF NOT EXISTS customers (
  tenant_id text NOT NULL, customer_id text NOT NULL, name text NOT NULL,
  status text NOT NULL, note text NOT NULL DEFAULT '', version int NOT NULL DEFAULT 1,
  PRIMARY KEY (tenant_id, customer_id));
CREATE TABLE IF NOT EXISTS documents (
  tenant_id text NOT NULL, document_id text NOT NULL, body text NOT NULL,
  PRIMARY KEY (tenant_id, document_id));
CREATE TABLE IF NOT EXISTS approvals (
  approval_id text PRIMARY KEY, actor text NOT NULL, tenant_id text NOT NULL,
  customer_id text NOT NULL, expected_version int NOT NULL, args_hash text NOT NULL,
  payload jsonb NOT NULL, state text NOT NULL, expires_at bigint NOT NULL,
  nonce text NOT NULL UNIQUE, capability text, result jsonb);
CREATE TABLE IF NOT EXISTS idempotency (
  tenant_id text NOT NULL, actor text NOT NULL, approval_id text NOT NULL,
  idem_key text NOT NULL, response jsonb NOT NULL,
  PRIMARY KEY (tenant_id, actor, approval_id, idem_key));
CREATE TABLE IF NOT EXISTS call_limits (
  tenant_id text NOT NULL, actor text NOT NULL, minute_bucket bigint NOT NULL,
  call_count int NOT NULL, PRIMARY KEY (tenant_id, actor, minute_bucket));
CREATE TABLE IF NOT EXISTS audit_events (
  seq bigserial PRIMARY KEY, event_id text UNIQUE NOT NULL, ts timestamptz NOT NULL,
  actor text NOT NULL, tenant_id text NOT NULL, action text NOT NULL,
  resource text NOT NULL, decision text NOT NULL, detail jsonb NOT NULL,
  prev_hash text NOT NULL, event_hash text NOT NULL);
CREATE TABLE IF NOT EXISTS schema_migrations (
  version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
