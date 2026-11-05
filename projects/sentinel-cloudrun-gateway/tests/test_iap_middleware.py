"""ASGI-level tests for IAP fail-closed identity propagation and spoofed headers."""
import asyncio
import json
import unittest
from unittest.mock import patch

from sentinel.security import AuthenticationError, Principal
from sentinel.api import IAPAuthenticationMiddleware


async def run_middleware(headers, claims=None, fail=False):
    captured = {}

    async def inner(scope, _receive, send):
        captured["authorization"] = [v.decode() for k, v in scope["headers"] if k.lower() == b"authorization"]
        body = b'{"ok":true}'
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})

    scope = {"type": "http", "path": "/v1/session", "method": "GET", "headers": headers, "query_string": b"", "scheme": "https", "server": ("localhost", 443), "client": ("127.0.0.1", 1), "http_version": "1.1"}
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    with patch("sentinel.api.AUTH_MODE", "iap"), patch("sentinel.api.IAP_AUDIENCE", "/projects/123/locations/us-central1/services/sentinel"), patch("sentinel.api.IAP_IDENTITIES", {"owner@example.test": Principal("alice", "tenant-a", "owner", "owner@example.test")}):
        if fail:
            verifier = patch("sentinel.api.verify_iap_assertion", side_effect=AuthenticationError("invalid"))
        else:
            verifier = patch("sentinel.api.verify_iap_assertion", return_value=claims or {"iss": "https://cloud.google.com/iap", "aud": "/projects/123/locations/us-central1/services/sentinel", "sub": "subject-1", "email": "owner@example.test"})
        with verifier:
            await IAPAuthenticationMiddleware(inner)(scope, receive, send)
    return captured, messages


class IapMiddlewareTests(unittest.TestCase):
    def test_spoofed_authorization_is_replaced_with_mapped_identity(self):
        captured, messages = asyncio.run(run_middleware([(b"authorization", b"Bearer attacker"), (b"x-goog-iap-jwt-assertion", b"signed")]))
        self.assertEqual(captured["authorization"], ["Bearer sentinel-iap:owner@example.test"])
        self.assertEqual(messages[0]["status"], 200)

    def test_invalid_or_unmapped_assertions_fail_closed(self):
        _, invalid = asyncio.run(run_middleware([(b"authorization", b"Bearer attacker")], fail=True))
        _, unknown = asyncio.run(run_middleware([(b"x-goog-iap-jwt-assertion", b"signed")], claims={"sub": "subject-2", "email": "unknown@example.test"}))
        self.assertEqual(invalid[0]["status"], 401)
        self.assertEqual(json.loads(invalid[1]["body"]), {"detail": "Verified IAP identity required"})
        self.assertEqual(unknown[0]["status"], 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)
