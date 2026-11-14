"""Input sanitization, prompt-injection defense and SSRF protection.

Every article, RSS item and webpage is treated as untrusted. Untrusted text
is never allowed to override system instructions: it is always wrapped in
clearly delimited blocks before being handed to an LLM.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Patterns that commonly appear in prompt-injection attempts embedded in
# scraped content. We neutralise them rather than execute them.
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"disregard\s+the\s+above", re.I),
    re.compile(r"system\s*prompt", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"</?\s*system\s*>", re.I),
]

_PRIVATE_HOST_SUFFIXES = (".local", ".internal", ".localhost")


def strip_html(raw: str) -> str:
    """Remove scripts/styles and return readable text from HTML."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def neutralize_injection(text: str) -> str:
    """Defang obvious prompt-injection phrases inside untrusted content."""
    cleaned = text or ""
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[redacted-instruction]", cleaned)
    return cleaned


def wrap_untrusted(text: str, label: str = "ARTICLE") -> str:
    """Wrap untrusted content in explicit delimiters for safe LLM use."""
    safe = neutralize_injection(strip_html(text))
    return f"<<<BEGIN_UNTRUSTED_{label}>>>\n{safe}\n<<<END_UNTRUSTED_{label}>>>"


def truncate(text: str, max_chars: int = 6000) -> str:
    """Bound the size of text passed to an LLM."""
    if not text:
        return ""
    return text if len(text) <= max_chars else text[:max_chars] + " …[truncated]"


def is_safe_url(url: str) -> bool:
    """Reject URLs that could be used for SSRF (private / loopback / non-http)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    if host.endswith(_PRIVATE_HOST_SUFFIXES) or host == "localhost":
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        # Hostname (not an IP literal) - allowed; DNS resolution is not performed here.
        pass
    return True


_SECRET_PATTERN = re.compile(
    r"(api[_-]?key|token|secret|password|authorization)\s*[=:]\s*\S+", re.I
)


def redact_secrets(text: str) -> str:
    """Redact secret-looking key/value pairs for safe logging."""
    if not text:
        return ""
    return _SECRET_PATTERN.sub(r"\1=[REDACTED]", text)
