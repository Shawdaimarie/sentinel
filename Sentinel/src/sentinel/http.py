"""Governed HTTP retrieval shared by the crawler and verifier.

Redirects are not followed automatically. Each hop is submitted to the agent's
``act`` so the policy engine evaluates the new location; a redirect from an
allowed host to a foreign one is denied and logged. Response bodies are
bounded in size and restricted to textual content types.
"""

from __future__ import annotations

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
    if content_type and not content_type.startswith(TEXT_TYPES):
        raise RetrievalError(f"content type {content_type!r} is not textual")
    if len(response.content) > MAX_BODY_BYTES:
        raise RetrievalError(f"response exceeds {MAX_BODY_BYTES} bytes")


def make_client(timeout: float) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
    )
