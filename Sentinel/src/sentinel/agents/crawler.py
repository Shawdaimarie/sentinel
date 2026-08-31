"""Crawler agent.

Retrieves pages from the monitored domain and extracts candidate claims. A
claim, for this purpose, is a sentence that asserts a quantity — a
percentage, a count, a latency, an uptime figure. These are the statements a
reader is most likely to take as fact and least able to check.

Extraction is heuristic by design: false positives are cheap (the verifier
will discard them); false negatives are not.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import httpx

from sentinel.agents.base import Agent
from sentinel.http import governed_get, make_client
from sentinel.models import Claim

_QUANTITY = re.compile(
    r"(\d[\d,.]*\s*(%|percent|ms|milliseconds|x|×)|\b\d{2,3}\.\d{1,3}\s*%|"
    r"\b\d[\d,]*\+?\s+(clients?|users?|deployments?|artefacts?|artifacts?|environments?))",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_BLOCK_TAGS = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "div",
        "section",
        "article",
        "title",
        "td",
        "th",
    }
)


class _TextExtractor(HTMLParser):
    """Collects visible text and hyperlinks, ignoring script and style."""

    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self.links: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        if tag in _BLOCK_TAGS:
            self.chunks.append("\n")
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag in _BLOCK_TAGS:
            self.chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.chunks.append(data.strip())


class Crawler(Agent):
    name = "crawler"

    def __init__(self, *args: Any, timeout: float = 15.0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client = make_client(timeout)
        self.register("http.get", self._get)

    def _get(self, target: str, _: dict[str, Any]) -> httpx.Response:
        return self._client.get(target)

    def crawl(self, url: str) -> list[Claim]:
        """Fetch one page and return the quantitative claims it makes."""
        sequence, body = governed_get(self, self._client, url)
        parser = _TextExtractor()
        parser.feed(body)
        text = re.sub(r"[ \t]+", " ", " ".join(parser.chunks))

        claims: list[Claim] = []
        for sentence in _SENTENCE_SPLIT.split(text):
            sentence = re.sub(r"\s+([.,;:!?])", r"\1", sentence.strip())
            if 20 <= len(sentence) <= 400 and _QUANTITY.search(sentence):
                claims.append(
                    Claim(
                        text=sentence,
                        source_url=url,
                        evidence_urls=_absolute_links(url, parser.links),
                        audit_sequence=sequence,
                    )
                )
        return claims

    def close(self) -> None:
        self._client.close()


def _absolute_links(base: str, links: list[str]) -> list[str]:
    """Resolve links against the page URL, keeping only HTTP(S) targets, de-duplicated."""
    seen: dict[str, None] = {}
    for link in links:
        absolute = urljoin(base, link)
        if absolute.startswith(("http://", "https://")):
            seen.setdefault(absolute, None)
    return list(seen)
