"""Authentication configuration and verified IAP identity mapping."""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping

from google.auth.transport.requests import Request
from google.oauth2 import id_token
import jwt

IAP_ISSUER = "https://cloud.google.com/iap"
IAP_CERTS_URL = "https://www.gstatic.com/iap/verify/public_key"
LOCAL_SECRET = "local-demo-secret-change-me"
LOCAL_DATABASE_URL = "postgresql://sentinel:local-only@localhost/sentinel"


class AuthenticationConfigurationError(ValueError):
    pass


class AuthenticationError(ValueError):
    pass


@dataclass(frozen=True)
class Principal:
    actor: str
    tenant_id: str
    role: str
    email: str | None = None
    subject: str | None = None


def parse_iap_identities(value: str | Mapping[str, Any] | None) -> dict[str, Principal]:
    if value is None or value == "":
        return {}
    try:
        raw = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError) as exc:
        raise AuthenticationConfigurationError("SENTINEL_IAP_IDENTITIES must be a JSON object") from exc
    if not isinstance(raw, dict):
        raise AuthenticationConfigurationError("SENTINEL_IAP_IDENTITIES must be a JSON object")
    if not raw:
        return {}
    identities: dict[str, Principal] = {}
    actors: set[str] = set()
    for email, details in raw.items():
        normalized_email = str(email).strip().lower()
        if not normalized_email or "@" not in normalized_email or not isinstance(details, dict):
            raise AuthenticationConfigurationError("Each IAP identity needs an email and a role mapping")
        actor = details.get("actor")
        tenant = details.get("tenant_id")
        role = details.get("role")
        if not isinstance(actor, str) or not re.fullmatch(r"[A-Za-z0-9_.@-]{1,80}", actor):
            raise AuthenticationConfigurationError("IAP actor IDs must be bounded identifiers")
        if not isinstance(tenant, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", tenant):
            raise AuthenticationConfigurationError("IAP tenant IDs must be bounded identifiers")
        if role not in ("owner", "admin"):
            raise AuthenticationConfigurationError("IAP role must be owner or admin")
        if normalized_email in identities or actor in actors:
            raise AuthenticationConfigurationError("IAP emails and actor IDs must be unique")
        identities[normalized_email] = Principal(actor=actor, tenant_id=tenant, role=role, email=normalized_email)
        actors.add(actor)
    roles = {principal.role for principal in identities.values()}
    if not {"owner", "admin"}.issubset(roles):
        raise AuthenticationConfigurationError("IAP configuration needs distinct owner and admin identities")
    owner_emails = {email for email, principal in identities.items() if principal.role == "owner"}
    admin_emails = {email for email, principal in identities.items() if principal.role == "admin"}
    if owner_emails & admin_emails:
        raise AuthenticationConfigurationError("Owner and approver identities must be separate")
    return identities


def validate_auth_configuration(
    *,
    environment: str,
    mode: str,
    token_map: Mapping[str, str],
    secret: str,
    database_url: str,
    iap_audience: str,
    iap_identities: Mapping[str, Principal],
    oidc_issuer: str = "",
    oidc_jwks_url: str = "",
    oidc_audience: str = "",
    oidc_identities: Mapping[str, Principal] | None = None,
) -> None:
    if mode not in ("local", "iap", "oidc"):
        raise AuthenticationConfigurationError("SENTINEL_AUTH_MODE must be local, iap, or oidc")
    if environment not in ("local", "staging", "production"):
        raise AuthenticationConfigurationError("SENTINEL_ENVIRONMENT must be local, staging, or production")
    if environment == "local" and mode != "local":
        raise AuthenticationConfigurationError("Federated authentication requires an explicit non-local environment")
    if environment != "local" and mode == "local":
        raise AuthenticationConfigurationError("Local fixture identity is allowed only in local environment")
    if mode == "local":
        if environment != "local":
            raise AuthenticationConfigurationError("Local fixture identity is allowed only in local environment")
        return
    if secret == LOCAL_SECRET or len(secret) < 32:
        raise AuthenticationConfigurationError("Production capability secret must be a managed value of at least 32 characters")
    if not database_url or database_url == LOCAL_DATABASE_URL:
        raise AuthenticationConfigurationError("Production DATABASE_URL must target the configured managed database")
    if token_map:
        raise AuthenticationConfigurationError("Local bearer fixtures are forbidden outside local mode")
    if mode == "iap":
        if not re.fullmatch(r"/projects/[0-9]+/locations/[a-z0-9-]+/services/[a-z0-9-]+", iap_audience):
            raise AuthenticationConfigurationError("IAP audience must identify the Cloud Run project, region, and service")
        if not iap_identities:
            raise AuthenticationConfigurationError("Production IAP identity role mappings are required")
    if mode == "oidc":
        if not oidc_issuer.startswith("https://") or not oidc_jwks_url.startswith("https://") or not oidc_audience:
            raise AuthenticationConfigurationError("OIDC issuer, HTTPS JWKS URL, and audience are required")
        if not oidc_identities:
            raise AuthenticationConfigurationError("Production OIDC subject role mappings are required")


class CachedIapCertificateRequest:
    """Cache IAP signing keys briefly so request validation does not fetch per call."""

    def __init__(self, ttl_seconds: int = 300):
        self._request = Request()
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._certs: dict[str, str] | None = None
        self._expires_at = 0.0

    def __call__(self, url: str, method: str = "GET", body: bytes | None = None, headers: Mapping[str, str] | None = None, timeout: float = 5, **kwargs: Any):
        if url != IAP_CERTS_URL or method != "GET":
            return self._request(url, method=method, body=body, headers=headers, timeout=timeout, **kwargs)
        now = time.monotonic()
        with self._lock:
            if self._certs is None or now >= self._expires_at:
                response = self._request(url, method="GET", headers=headers, timeout=timeout)
                if response.status != 200:
                    raise AuthenticationError("IAP signing certificate fetch failed")
                try:
                    certs = json.loads(response.data)
                except (TypeError, json.JSONDecodeError) as exc:
                    raise AuthenticationError("IAP signing certificate response was invalid") from exc
                if not isinstance(certs, dict) or not certs:
                    raise AuthenticationError("IAP signing certificate response was empty")
                self._certs = certs
                self._expires_at = now + self._ttl_seconds
            return type("CachedResponse", (), {"status": 200, "data": json.dumps(self._certs).encode(), "headers": {}})()


_iap_certificate_request = CachedIapCertificateRequest()


def verify_iap_assertion(token: str, audience: str, request: Any = None) -> Mapping[str, Any]:
    try:
        claims = id_token.verify_token(
            token,
            request or _iap_certificate_request,
            audience=audience,
            certs_url=IAP_CERTS_URL,
            clock_skew_in_seconds=30,
        )
    except Exception as exc:
        raise AuthenticationError("IAP assertion signature, audience, or time validation failed") from exc
    if claims.get("iss") != IAP_ISSUER:
        raise AuthenticationError("IAP assertion issuer is invalid")
    if not claims.get("sub") or not claims.get("email"):
        raise AuthenticationError("IAP assertion is missing the subject or email")
    return claims


def principal_for_iap_claims(claims: Mapping[str, Any], identities: Mapping[str, Principal]) -> Principal:
    email = str(claims.get("email", "")).strip().lower()
    configured = identities.get(email)
    if not configured:
        raise AuthenticationError("IAP-authenticated identity is not assigned to this SENTINEL tenant")
    return Principal(
        actor=configured.actor,
        tenant_id=configured.tenant_id,
        role=configured.role,
        email=email,
        subject=str(claims["sub"]),
    )


def parse_oidc_identities(value: str | Mapping[str, Any] | None) -> dict[str, Principal]:
    """Map exact issuer subjects to tenant roles; never trust role claims from a JWT."""
    if value is None or value == "":
        return {}
    try:
        raw = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError) as exc:
        raise AuthenticationConfigurationError("SENTINEL_OIDC_IDENTITIES must be a JSON object") from exc
    if not isinstance(raw, dict):
        raise AuthenticationConfigurationError("SENTINEL_OIDC_IDENTITIES must be a JSON object")
    if not raw:
        return {}
    result: dict[str, Principal] = {}
    actors: set[str] = set()
    for subject, details in raw.items():
        if not isinstance(subject, str) or not subject.strip() or not isinstance(details, dict):
            raise AuthenticationConfigurationError("OIDC identities must map exact subjects to role mappings")
        actor, tenant, role = details.get("actor"), details.get("tenant_id"), details.get("role")
        if not isinstance(actor, str) or not re.fullmatch(r"[A-Za-z0-9_.@-]{1,80}", actor):
            raise AuthenticationConfigurationError("OIDC actor IDs must be bounded identifiers")
        if not isinstance(tenant, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", tenant) or role not in ("owner", "admin"):
            raise AuthenticationConfigurationError("OIDC tenant and role mapping is invalid")
        if subject in result or actor in actors:
            raise AuthenticationConfigurationError("OIDC subjects and actor IDs must be unique")
        result[subject] = Principal(actor=actor, tenant_id=tenant, role=role, subject=subject)
        actors.add(actor)
    roles = {p.role for p in result.values()}
    if not {"owner", "admin"}.issubset(roles):
        raise AuthenticationConfigurationError("OIDC configuration needs distinct owner and admin subjects")
    return result


def verify_oidc_assertion(token: str, *, issuer: str, jwks_url: str, audience: str) -> Mapping[str, Any]:
    if not token or len(token) > 16384 or not issuer.startswith("https://") or not jwks_url.startswith("https://"):
        raise AuthenticationError("OIDC bearer assertion or verifier configuration is invalid")
    try:
        signing_key = _oidc_jwk_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "aud", "iss"], "verify_signature": True},
            leeway=30,
        )
    except Exception as exc:
        raise AuthenticationError("OIDC signature, issuer, audience, or time validation failed") from exc
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise AuthenticationError("OIDC assertion subject is invalid")
    return claims


@lru_cache(maxsize=8)
def _oidc_jwk_client(jwks_url: str):
    """Reuse a bounded JWKS cache per operator-configured HTTPS endpoint."""
    return jwt.PyJWKClient(jwks_url, timeout=5, cache_keys=True)
