"""Cryptographic OIDC verifier regressions. Run with the pinned gateway dependencies."""
import time
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from sentinel.security import (
    AuthenticationConfigurationError,
    AuthenticationError,
    parse_oidc_identities,
    validate_auth_configuration,
    verify_oidc_assertion,
)

ISSUER = "https://issuer.example.test"
JWKS = "https://issuer.example.test/.well-known/jwks.json"
AUDIENCE = "sentinel-staging"
NOW = int(time.time())
PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC = PRIVATE.public_key()


class SigningKey:
    key = PUBLIC


class SigningKeyClient:
    def __init__(self, *_args, **_kwargs):
        pass

    def get_signing_key_from_jwt(self, _token):
        return SigningKey()


def token(**overrides):
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": "owner-sub", "iat": NOW, "exp": NOW + 120}
    claims.update(overrides)
    return jwt.encode(claims, PRIVATE, algorithm="RS256", headers={"kid": "test-key"})


class OidcVerifierTests(unittest.TestCase):
    def test_valid_signed_assertion_and_subject_mapping(self):
        with patch("sentinel.security.jwt.PyJWKClient", SigningKeyClient):
            claims = verify_oidc_assertion(token(), issuer=ISSUER, jwks_url=JWKS, audience=AUDIENCE)
        mapped = parse_oidc_identities({
            "owner-sub": {"actor": "alice", "tenant_id": "tenant-a", "role": "owner"},
            "admin-sub": {"actor": "operator", "tenant_id": "tenant-a", "role": "admin"},
        })
        self.assertEqual(mapped[claims["sub"]].actor, "alice")

    def test_rejects_bad_signature(self):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        bad = jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "sub": "owner-sub", "iat": NOW, "exp": NOW + 120}, other_key, algorithm="RS256", headers={"kid": "test-key"})
        with patch("sentinel.security.jwt.PyJWKClient", SigningKeyClient):
            with self.assertRaises(AuthenticationError):
                verify_oidc_assertion(bad, issuer=ISSUER, jwks_url=JWKS, audience=AUDIENCE)

    def test_rejects_wrong_issuer_audience_and_expiry(self):
        with patch("sentinel.security.jwt.PyJWKClient", SigningKeyClient):
            for claims in ({"iss": "https://wrong.test"}, {"aud": "other-service"}, {"exp": NOW - 120}):
                with self.subTest(claims=claims), self.assertRaises(AuthenticationError):
                    verify_oidc_assertion(token(**claims), issuer=ISSUER, jwks_url=JWKS, audience=AUDIENCE)

    def test_requires_critical_claims(self):
        with patch("sentinel.security.jwt.PyJWKClient", SigningKeyClient):
            for claim in ("exp", "iat", "sub", "aud", "iss"):
                claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": "owner-sub", "iat": NOW, "exp": NOW + 120}
                claims.pop(claim)
                with self.subTest(claim=claim), self.assertRaises(AuthenticationError):
                    missing_claim = jwt.encode(claims, PRIVATE, algorithm="RS256", headers={"kid": "test-key"})
                    verify_oidc_assertion(missing_claim, issuer=ISSUER, jwks_url=JWKS, audience=AUDIENCE)

    def test_rejects_unknown_algorithm_even_when_jwt_header_selects_it(self):
        bad = jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "sub": "owner-sub", "iat": NOW, "exp": NOW + 120}, "symmetric-test-only", algorithm="HS256", headers={"kid": "test-key"})
        with patch("sentinel.security.jwt.PyJWKClient", SigningKeyClient):
            with self.assertRaises(AuthenticationError):
                verify_oidc_assertion(bad, issuer=ISSUER, jwks_url=JWKS, audience=AUDIENCE)

    def test_rejects_local_auth_or_untrusted_urls_in_production(self):
        with self.assertRaises(AuthenticationConfigurationError):
            validate_auth_configuration(environment="development", mode="iap", token_map={}, secret="x" * 40, database_url="postgresql://managed", iap_audience="/projects/123/locations/us-central1/services/sentinel", iap_identities={})
        with self.assertRaises(AuthenticationConfigurationError):
            validate_auth_configuration(environment="staging", mode="oidc", token_map={}, secret="x" * 40, database_url="postgresql://managed", iap_audience="", iap_identities={}, oidc_issuer=ISSUER, oidc_jwks_url="http://metadata.google.internal/", oidc_audience=AUDIENCE, oidc_identities={})


if __name__ == "__main__":
    unittest.main(verbosity=2)
