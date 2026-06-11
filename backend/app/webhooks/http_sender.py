"""Real HTTP webhook sender with SSRF protection.

Replaces the offline no-op sender for live deployments. Delivers a signed webhook payload
over HTTPS with a bounded timeout, but only after the destination URL passes an SSRF guard:
the scheme must be https (http allowed only when explicitly enabled), and the host - plus
every IP it resolves to - must not be loopback, link-local, private, multicast, reserved, or
the cloud metadata address (169.254.169.254).

The sender keeps the dispatcher's contract ``async (url, headers, body) -> int`` so the
existing retry / dead-letter / outbox machinery is unchanged. An httpx transport can be
injected for deterministic tests (no real network).
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

# Cloud metadata endpoint (AWS/GCP/Azure) - never a legitimate webhook target.
_METADATA_IPS = {"169.254.169.254", "fd00:ec2::254"}


class WebhookSecurityError(Exception):
    """Raised when a webhook URL fails the SSRF safety check."""


def _ip_is_blocked(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # unparseable -> reject
    return (
        addr.is_loopback
        or addr.is_link_local
        or addr.is_private
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
        or ip in _METADATA_IPS
    )


def _resolve_ips(host: str) -> list[str]:
    """Resolve a host to all its IPs. Raises on failure (treated as unsafe)."""
    infos = socket.getaddrinfo(host, None)
    return [info[4][0] for info in infos]


def assert_safe_url(url: str, *, allow_http: bool = False) -> None:
    """Raise :class:`WebhookSecurityError` if the URL is unsafe to call.

    Checks scheme, presence of a host, the literal metadata address, and every resolved IP.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme == "http" and not allow_http:
        raise WebhookSecurityError("http not allowed (use https)")
    if scheme not in ("http", "https"):
        raise WebhookSecurityError(f"unsupported scheme: {scheme or '(none)'}")

    host = parsed.hostname
    if not host:
        raise WebhookSecurityError("missing host")

    # Direct literal metadata host / IP.
    if host in _METADATA_IPS:
        raise WebhookSecurityError("metadata address blocked")

    # If the host is already an IP literal, check it directly; else resolve.
    try:
        ipaddress.ip_address(host)
        candidates = [host]
    except ValueError:
        try:
            candidates = _resolve_ips(host)
        except socket.gaierror as exc:
            raise WebhookSecurityError(f"cannot resolve host: {host}") from exc

    for ip in candidates:
        if _ip_is_blocked(ip):
            raise WebhookSecurityError(f"blocked destination IP: {ip}")


class HttpWebhookSender:
    """Async webhook sender backed by httpx, with an SSRF guard.

    Callable as ``await sender(url, headers, body) -> status_code`` to match the
    dispatcher's Sender contract. A blocked URL raises :class:`WebhookSecurityError`
    before any network call (the dispatcher records it as a failed delivery).
    """

    def __init__(
        self,
        *,
        timeout: float = 5.0,
        allow_http: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = timeout
        self._allow_http = allow_http
        self._transport = transport

    async def __call__(self, url: str, headers: dict[str, str], body: bytes) -> int:
        assert_safe_url(url, allow_http=self._allow_http)
        async with httpx.AsyncClient(
            timeout=self._timeout, transport=self._transport
        ) as client:
            response = await client.post(url, content=body, headers=headers)
            return response.status_code
