# Authentication configuration contract

The gateway fails during startup when a non-local deployment has missing or invalid authentication configuration. The production UI is bundled into the gateway image and uses same-origin calls, so Cloud Run IAP can protect both `/` and `/v1/*` through the same service.

## Local synthetic mode

`SENTINEL_ENVIRONMENT=local`, `SENTINEL_AUTH_MODE=local`, and the demo bearer token map are for synthetic local runs only. The gateway rejects this mode if the environment is staging or production.

## Google Cloud Run with IAP

Set `SENTINEL_ENVIRONMENT=staging` (or `production`) and `SENTINEL_AUTH_MODE=iap`. Supply:

| Variable | Required value |
| --- | --- |
| `SENTINEL_IAP_AUDIENCE` | `/projects/PROJECT_NUMBER/locations/REGION/services/SERVICE_NAME` |
| `SENTINEL_IAP_IDENTITIES` | JSON email-keyed map of `{ "actor": "...", "tenant_id": "...", "role": "owner" | "admin" }` |
| `SENTINEL_LOCAL_TOKENS` | Empty JSON object (`{}`) |
| `CAPABILITY_SECRET` | Secret Manager supplied random value, at least 32 characters |
| `DATABASE_URL` | Managed PostgreSQL connection string; never the local fixture URL |

Before deploying a new image, run `python tools/migrate.py` from the same immutable gateway image with a short-lived operator connection in `SENTINEL_MIGRATION_DATABASE_URL` and `SENTINEL_RUNTIME_DB_ROLE` naming the pre-created runtime role. The runtime `DATABASE_URL` must authenticate as that restricted role, not the migration owner. The migration command grants only the API's required table operations, grants append-only access to audit events, and withholds schema creation. The Cloud Run service must never receive the migration credential.

The IAP middleware verifies each assertion signature with Google's published IAP signing keys and checks issuer, audience, issue time, and expiry. The email is only accepted if it has an explicit tenant/role mapping. Application role claims are never inferred from a request header. Owner and admin mappings must use distinct email identities and actor IDs.

## Other OIDC providers

For a provider that supplies a signed bearer JWT to the gateway, set `SENTINEL_ENVIRONMENT=staging` (or `production`) and `SENTINEL_AUTH_MODE=oidc`. Supply:

| Variable | Required value |
| --- | --- |
| `SENTINEL_OIDC_ISSUER` | Exact HTTPS issuer configured by the operator |
| `SENTINEL_OIDC_JWKS_URL` | Operator-configured HTTPS JWKS endpoint; metadata/private-network URLs are rejected |
| `SENTINEL_OIDC_AUDIENCE` | Exact gateway audience |
| `SENTINEL_OIDC_IDENTITIES` | JSON map keyed by exact `sub` to `{ "actor": "...", "tenant_id": "...", "role": "owner" | "admin" }` |
| `SENTINEL_LOCAL_TOKENS` | Empty JSON object (`{}`) |
| `CAPABILITY_SECRET` | Secret Manager supplied random value, at least 32 characters |
| `DATABASE_URL` | Managed PostgreSQL connection string; never the local fixture URL |

Run the migration command with a separate operator identity before each application rollout. The task/runtime secret must contain credentials for the restricted runtime role, not the migration role.

OIDC verification restricts algorithms to RS256 and ES256 and requires signature, exact issuer and audience, expiry, issue time, subject, and audience claims. Tenant and role are resolved only from the configured exact-subject map. The hosting platform must ensure the bearer JWT reaches the service only over TLS and must not replace authorization with unverified identity headers.

## Browser integration

Cloud Run IAP provides browser identity and injects the signed IAP assertion. Generic OIDC mode currently validates bearer JWTs for API clients; a hosting provider still needs an operator-configured browser sign-in/token delivery mechanism before the UI can be used interactively. Never expose capability secrets or bearer tokens to frontend build variables.
