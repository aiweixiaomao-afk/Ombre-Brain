"""Loopback MCP DNS-rebinding allowlist includes the configured public host."""

from __future__ import annotations

from mcp.server.transport_security import TransportSecurityMiddleware

from ombrebrain.security.mcp_transport import build_mcp_transport_security


def test_loopback_public_origin_allows_proxy_host_and_chatgpt_origin() -> None:
    settings = build_mcp_transport_security(
        bind_host="127.0.0.1",
        public_origin="https://ob.aiwei.asia/mcp",
    )
    assert settings is not None
    assert settings.enable_dns_rebinding_protection is True
    guard = TransportSecurityMiddleware(settings)

    assert guard._validate_host("ob.aiwei.asia")
    assert guard._validate_host("ob.aiwei.asia:443")
    assert guard._validate_host("127.0.0.1:18001")
    assert guard._validate_host("localhost:18001")
    assert not guard._validate_host("evil.example")

    assert guard._validate_origin(None)
    assert guard._validate_origin("https://ob.aiwei.asia")
    assert guard._validate_origin("https://chatgpt.com")
    assert guard._validate_origin("https://chat.openai.com")
    assert not guard._validate_origin("https://evil.example")


def test_loopback_without_public_origin_keeps_sdk_default() -> None:
    assert (
        build_mcp_transport_security(bind_host="127.0.0.1", public_origin="")
        is None
    )


def test_non_loopback_bind_is_left_to_the_sdk() -> None:
    assert (
        build_mcp_transport_security(
            bind_host="0.0.0.0",
            public_origin="https://ob.aiwei.asia",
        )
        is None
    )


def test_extra_origin_is_added_and_junk_is_ignored() -> None:
    settings = build_mcp_transport_security(
        bind_host="localhost",
        public_origin="https://ob.aiwei.asia",
        extra_origins="https://claude.ai, *, https://evil.example/path",
    )
    assert settings is not None
    guard = TransportSecurityMiddleware(settings)
    assert guard._validate_origin("https://claude.ai")
    assert not guard._validate_origin("*")
    assert not guard._validate_origin("https://evil.example/path")
