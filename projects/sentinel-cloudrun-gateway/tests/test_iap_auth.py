"""Signed IAP assertion checks against an ephemeral X.509 certificate."""
import json
import time
import unittest
from datetime import datetime, timedelta, timezone

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from sentinel.security import AuthenticationError, verify_iap_assertion, IAP_CERTS_URL

AUDIENCE = "/projects/123456789/locations/us-central1/services/sentinel"
PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
NOW = datetime.now(timezone.utc)
SUBJECT = ISSUER_NAME = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "SENTINEL test IAP key")])
CERT = (
    x509.CertificateBuilder()
    .subject_name(SUBJECT)
    .issuer_name(ISSUER_NAME)
    .public_key(PRIVATE.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(NOW - timedelta(minutes=1))
    .not_valid_after(NOW + timedelta(days=1))
    .sign(PRIVATE, hashes.SHA256())
).public_bytes(serialization.Encoding.PEM).decode()


class CertRequest:
    def __call__(self, url, method="GET", **_kwargs):
        if url != IAP_CERTS_URL or method != "GET":
            raise AssertionError("Unexpected certificate URL")
        return type("Response", (), {"status": 200, "data": json.dumps({"test-key": CERT}).encode(), "headers": {}})()


def assertion(**overrides):
    now = int(time.time())
    claims = {"iss": "https://cloud.google.com/iap", "aud": AUDIENCE, "sub": "accounts.google.com:123", "email": "owner@example.test", "iat": now, "exp": now + 120}
    claims.update(overrides)
    return jwt.encode(claims, PRIVATE, algorithm="RS256", headers={"kid": "test-key"})


class IapVerifierTests(unittest.TestCase):
    def test_valid_signed_assertion(self):
        claims = verify_iap_assertion(assertion(), AUDIENCE, CertRequest())
        self.assertEqual(claims["email"], "owner@example.test")

    def test_rejects_bad_signature(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = int(time.time())
        bad = jwt.encode({"iss": "https://cloud.google.com/iap", "aud": AUDIENCE, "sub": "s", "email": "a@example.test", "iat": now, "exp": now + 120}, other, algorithm="RS256", headers={"kid": "test-key"})
        with self.assertRaises(AuthenticationError):
            verify_iap_assertion(bad, AUDIENCE, CertRequest())

    def test_rejects_wrong_audience_and_expired_assertion(self):
        for claims in ({"aud": "/projects/other"}, {"exp": int(time.time()) - 120}):
            with self.subTest(claims=claims), self.assertRaises(AuthenticationError):
                verify_iap_assertion(assertion(**claims), AUDIENCE, CertRequest())

    def test_rejects_wrong_issuer_and_missing_identity(self):
        for claims in ({"iss": "https://issuer.example.test"}, {"sub": "", "email": ""}):
            with self.subTest(claims=claims), self.assertRaises(AuthenticationError):
                verify_iap_assertion(assertion(**claims), AUDIENCE, CertRequest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
