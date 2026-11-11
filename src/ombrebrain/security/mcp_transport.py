"""Host allowlist for MCP DNS-rebinding protection behind a reverse proxy.

FastMCP turns that protection on automatically when the process binds to
loopback, and the default allowlist is only localhost. A local Caddy or nginx
then forwards the public Host (for example ``ob.aiwei.asia``) and the SDK
answers ``421 Misdirected Request`` before the MCP session starts.

The allowlist stays explicit. Loopback entries remain, and the configured
public origin is added beside them. Protection is not switched off.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from mcp.server.transport_security import TransportSecuritySettings

from ombrebrain.security.public_origin import normalize_public_origin


_LOOPBACK_HOSTS = (
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
    "127.0.0.1",
    "localhost",
    "[::1]",
)
_LOOPBACK_ORIGINS = (
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
    "http://127.0.0.1",
    "http://localhost",
    "http://[::1]",
)
# Browser origins used by ChatGPT's custom MCP connector. Server-side calls
# usually omit Origin; these cover the cases that send one.
_PUBLIC_CLIENT_ORIGINS = (
    "https://chatgpt.com",
    "https://chatgpt.com:*",
    "https://chat.openai.com",
    "https://chat.openai.com:*",
)
_HOST_ENTRY = re.compile(
    r"^(?:\[[0-9A-Fa-f:]+\]|[A-Za-z0-9.-]+)(?::(?:\*|[0-9]{1,5}))?$"
)
_ORIGIN_ENTRY = re.compile(
    r"^https?://(?:\[[0-9A-Fa-f:]+\]|[A-Za-z0-9.-]+)(?::(?:\*|[0-9]{1,5}))?$"
)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _csv(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _host_patterns(origin: str) -> list[str]:
    parsed = urlsplit(origin)
    hostname = parsed.hostname or ""
    if not hostname:
        return []
    host = f"[{hostname}]" if ":" in hostname else hostname
    patterns = [host, f"{host}:*"]
    if parsed.port:
        patterns.append(f"{host}:{parsed.port}")
    return patterns


def _origin_patterns(origin: str) -> list[str]:
    return [origin, f"{origin}:*"]


def build_mcp_transport_security(
    *,
    bind_host: str,
    public_origin: str,
    extra_hosts: str = "",
    extra_origins: str = "",
) -> TransportSecuritySettings | None:
    """Return loopback-plus-public settings, or None to keep the SDK default.

    Non-loopback binds keep the SDK default (protection stays off). Turning it
    on there would reject Docker and PaaS Host headers that were previously
    accepted. Loopback binds keep protection on and add the public origin.
    """

    loopback = str(bind_host or "").strip() in {"127.0.0.1", "localhost", "::1"}
    if not loopback:
        return None

    origin = normalize_public_origin(public_origin)
    hosts = [item for item in _csv(extra_hosts) if _HOST_ENTRY.fullmatch(item)]
    origins = [item for item in _csv(extra_origins) if _ORIGIN_ENTRY.fullmatch(item)]
    if origin:
        hosts.extend(_host_patterns(origin))
        origins.extend(_origin_patterns(origin))
        if origin.startswith("https://"):
            origins.extend(_PUBLIC_CLIENT_ORIGINS)
    if not hosts and not origins:
        return None

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_dedupe([*_LOOPBACK_HOSTS, *hosts]),
        allowed_origins=_dedupe([*_LOOPBACK_ORIGINS, *origins]),
    )
