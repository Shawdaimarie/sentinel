"""Governed HTTP retrieval shared by the crawler and verifier.

Redirects are not followed automatically. Each hop is submitted to the agent's
``act`` so the policy engine evaluates the new location; a redirect from an
allowed host to a foreign one is denied and logged. Response bodies are
bounded in size and restricted to textual content types.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from sentinel.agents.base import Agent

MAX_REDIRECTS = 5
MAX_BODY_BYTES = 2 * 1024 * 1024
TEXT_TYPES = ("text/html", "text/plain", "application/xhtml+xml")
USER_AGENT = "sentinel/0.1 (+https://github.com/Shawdaimarie/sentinel)"


class RetrievalError(RuntimeError):
    """Raised when a response is unacceptable under the retrieval constraints."""


class PinnedAddressTransport(httpx.BaseTransport):
    """Connect to the validated IP while retaining the original Host and TLS name.

    No pooled keepalive connection is shared across hostnames with the same IP.
    DNS is checked here, immediately before connection, as well as by policy.
    """

    def __init__(self, *, allow_private_networks: bool = False) -> None:
        self.allow_private_networks = allow_private_networks
        self._transport = httpx.HTTPTransport(
            trust_env=False, limits=httpx.Limits(max_keepalive_connections=0)
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        try:
            addresses = sorted({str(info[4][0]) for info in socket.getaddrinfo(host, None)})
            if (
                not addresses
                or any(not ipaddress.ip_address(address).is_global for address in addresses)
                and not self.allow_private_networks
            ):
                raise RetrievalError("connection address is not permitted")
        except (OSError, ValueError) as exc:
            raise RetrievalError("connection address could not be validated") from exc
        pinned = httpx.Request(
            request.method,
            request.url.copy_with(host=addresses[0]),
            headers=request.headers,
            stream=request.stream,
            extensions={**request.extensions, "sni_hostname": host},
        )
        return self._transport.handle_request(pinned)

    def close(self) -> None:
        self._transport.close()


def bounded_get(client: httpx.Client, target: str) -> httpx.Response:
    """Limit decoded response bytes while receiving, including compressed bodies."""
    with client.stream("GET", target) as response:
        body = bytearray()
        if not response.is_redirect:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type and content_type not in TEXT_TYPES:
                raise RetrievalError(f"content type {content_type!r} is not textual")
            for chunk in response.iter_bytes(chunk_size=65536):
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    raise RetrievalError(f"response exceeds {MAX_BODY_BYTES} bytes")
                body.extend(chunk)
        headers = dict(response.headers)
        headers.pop("content-encoding", None)
        headers.pop("content-length", None)
        return httpx.Response(
            response.status_code, headers=headers, content=bytes(body), request=response.request
        )


def governed_get(agent: Agent, client: httpx.Client, url: str) -> tuple[int, str]:
    """Fetch ``url`` through the agent's policy, following redirects hop by hop.

    Returns the audit sequence of the final successful request and the body.
    """
    for _ in range(MAX_REDIRECTS + 1):
        record, response = agent.act("http.get", url)
        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                raise RetrievalError(f"redirect from {url} without a Location header")
            url = str(response.url.join(location))
            continue
        response.raise_for_status()
        _check_response(response)
        return record.sequence, response.text
    raise RetrievalError(f"more than {MAX_REDIRECTS} redirects from {url}")


def _check_response(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type and content_type not in TEXT_TYPES:
        raise RetrievalError(f"content type {content_type!r} is not textual")
    if len(response.content) > MAX_BODY_BYTES:
        raise RetrievalError(f"response exceeds {MAX_BODY_BYTES} bytes")


def make_client(timeout: float, *, allow_private_networks: bool = False) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
        transport=PinnedAddressTransport(allow_private_networks=allow_private_networks),
        headers={"User-Agent": USER_AGENT},
    )
