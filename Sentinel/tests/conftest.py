from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from sentinel.audit import AuditLog
from sentinel.policy import Policy, PolicyDocument

POLICY = Path(__file__).resolve().parents[1] / "policy.yaml"


def public_resolver(host: str) -> list[str]:
    """Deterministic resolver: the monitored domain maps to a global address."""
    if host.endswith("essentialdigitalsolution.com"):
        return ["1.1.1.1"]
    if host == "127.0.0.1":
        return ["127.0.0.1"]
    raise OSError(f"unresolvable test host {host}")


@pytest.fixture
def policy() -> Policy:
    return Policy.load(POLICY, resolver=public_resolver)


@pytest.fixture
def audit(tmp_path: Path) -> AuditLog:
    return AuditLog(tmp_path / "audit.jsonl", key=None)


@pytest.fixture
def local_policy() -> Policy:
    """Policy that permits the loopback test server for the crawler and verifier."""
    document = PolicyDocument.model_validate(
        {
            "version": 1,
            "defaults": {"decision": "deny"},
            "agents": {
                "crawler": {
                    "purpose": "test",
                    "allowed_actions": ["http.get"],
                    "allowed_domains": ["127.0.0.1"],
                    "allow_private_networks": True,
                    "max_actions_per_run": 50,
                },
                "verifier": {
                    "purpose": "test",
                    "allowed_actions": ["http.get"],
                    "allowed_domains": ["127.0.0.1"],
                    "allow_private_networks": True,
                    "max_actions_per_run": 50,
                },
            },
        }
    )
    return Policy(document, resolver=public_resolver)


class _Handler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, dict[str, str], bytes]] = {}

    def do_GET(self) -> None:  # noqa: N802 — required by BaseHTTPRequestHandler
        status, headers, body = self.routes.get(self.path, (404, {}, b"not found"))
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        pass


@pytest.fixture
def server() -> Iterator[str]:
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    base = f"http://127.0.0.1:{port}"
    _Handler.routes = {
        "/page": (
            200,
            {"Content-Type": "text/html"},
            b'<p>Uptime of 99.99% held. <a href="/evidence">Evidence</a>.</p>',
        ),
        "/evidence": (200, {"Content-Type": "text/html"}, b"<p>Observed 99.99% availability.</p>"),
        "/escape": (302, {"Location": "http://example.com/"}, b""),
        "/internal": (302, {"Location": f"{base}/page"}, b""),
        "/binary": (200, {"Content-Type": "application/octet-stream"}, b"\x00\x01"),
        "/loop": (302, {"Location": "/loop"}, b""),
    }
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield base
    httpd.shutdown()
