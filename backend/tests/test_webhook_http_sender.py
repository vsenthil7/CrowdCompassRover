"""Tests for the real HTTP webhook sender and its SSRF guard."""
from __future__ import annotations

import httpx
import pytest

from app.webhooks.http_sender import (
    HttpWebhookSender,
    WebhookSecurityError,
    assert_safe_url,
)


# --- assert_safe_url: rejections ---

def test_rejects_http_by_default():
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("http://example.com/hook")


def test_allows_http_when_enabled(monkeypatch):
    # A public-looking host over http should pass only when allow_http=True.
    # Use a literal public IP to avoid DNS in the test.
    assert_safe_url("http://93.184.216.34/hook", allow_http=True)


def test_rejects_unsupported_scheme():
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("ftp://example.com/hook")


def test_rejects_missing_host():
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("https:///nohost")


def test_rejects_metadata_host():
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("https://169.254.169.254/latest/meta-data/")


def test_rejects_loopback_ip():
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("https://127.0.0.1/hook")


def test_rejects_private_ip():
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("https://10.0.0.5/hook")
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("https://192.168.1.1/hook")


def test_rejects_link_local_ip():
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("https://169.254.10.10/hook")


def test_rejects_unresolvable_host():
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("https://nonexistent.invalid./hook")


def test_rejects_host_resolving_to_private(monkeypatch):
    # A public-looking name that resolves to a private IP must be blocked.
    import app.webhooks.http_sender as mod

    monkeypatch.setattr(mod, "_resolve_ips", lambda host: ["10.1.2.3"])
    with pytest.raises(WebhookSecurityError):
        assert_safe_url("https://sneaky.example.com/hook")


def test_allows_public_ip_literal():
    # Public IP literal passes (no DNS needed).
    assert_safe_url("https://93.184.216.34/hook")


def test_allows_public_host(monkeypatch):
    import app.webhooks.http_sender as mod

    monkeypatch.setattr(mod, "_resolve_ips", lambda host: ["93.184.216.34"])
    assert_safe_url("https://example.com/hook")  # no raise


# --- HttpWebhookSender: delivery ---

async def test_sender_posts_and_returns_status(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        captured["sig"] = request.headers.get("x-signature")
        return httpx.Response(202)

    sender = HttpWebhookSender(transport=httpx.MockTransport(handler))
    # Bypass DNS for the public host.
    import app.webhooks.http_sender as mod

    monkeypatch.setattr(mod, "_resolve_ips", lambda host: ["93.184.216.34"])

    status = await sender(
        "https://example.com/hook", {"x-signature": "sha256=abc"}, b'{"event":"x"}'
    )
    assert status == 202
    assert captured["body"] == b'{"event":"x"}'
    assert captured["sig"] == "sha256=abc"


async def test_sender_blocks_ssrf_before_network():
    # No transport call should happen for a blocked URL.
    sender = HttpWebhookSender()
    with pytest.raises(WebhookSecurityError):
        await sender("https://127.0.0.1/hook", {}, b"{}")


async def test_sender_allows_http_when_configured():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    sender = HttpWebhookSender(allow_http=True, transport=httpx.MockTransport(handler))
    status = await sender("http://93.184.216.34/hook", {}, b"{}")
    assert status == 200


# --- internal helpers ---

def test_ip_is_blocked_rejects_unparseable():
    import app.webhooks.http_sender as mod

    assert mod._ip_is_blocked("not-an-ip") is True


def test_resolve_ips_real_localhost():
    import app.webhooks.http_sender as mod

    ips = mod._resolve_ips("localhost")
    assert any(ip in ("127.0.0.1", "::1") for ip in ips)


# --- providers wiring ---

def test_live_mode_builds_http_sender(monkeypatch):
    from app.core.config import Settings, AppMode
    from app.core.providers import _build_webhook_sender

    settings = Settings(app_mode=AppMode.REAL)
    sender = _build_webhook_sender(settings)
    assert isinstance(sender, HttpWebhookSender)


def test_mock_mode_builds_noop_sender():
    from app.core.config import Settings, AppMode
    from app.core.providers import _build_webhook_sender

    settings = Settings(app_mode=AppMode.MOCK)
    sender = _build_webhook_sender(settings)
    assert not isinstance(sender, HttpWebhookSender)


async def test_mock_sender_returns_200():
    from app.core.config import Settings, AppMode
    from app.core.providers import _build_webhook_sender

    sender = _build_webhook_sender(Settings(app_mode=AppMode.MOCK))
    assert await sender("https://anything", {}, b"{}") == 200
