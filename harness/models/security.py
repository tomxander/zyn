"""Security helpers for model connectors: URL sanitization, secret scrubbing, and offline host validation."""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urlparse

import httpcore
import httpx

FORBIDDEN_ENV_PREFIXES = ("ZYN_", "DATABASE_", "SESSION_", "OIDC_")
FORBIDDEN_ENV_NAMES = {"SESSION_SECRET", "DB_PASSWORD", "OIDC_SECRET", "SECRET_KEY"}


def validate_api_key_env(env_var: str) -> str:
    """Refuses api_key_env names that could expose Zyn internal secrets."""
    upper = env_var.strip().upper()
    if upper in FORBIDDEN_ENV_NAMES or any(upper.startswith(p) for p in FORBIDDEN_ENV_PREFIXES):
        raise ValueError(
            f"api_key_env '{env_var}' is forbidden: cannot point to internal system secret variables"
        )
    return env_var.strip()


def sanitize_url(raw_url: str) -> str:
    """Removes userinfo (passwords) and query strings from URLs for safe logging and error reporting."""
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url)
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return parsed._replace(netloc=netloc, query="").geturl()
    except Exception:  # noqa: BLE001
        # Fallback strip
        return raw_url.split("@")[-1].split("?")[0]


# Forbidden metadata IP addresses (cloud instance metadata services)
BANNED_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("fd00:ec2::254"),
}


def scrub_error_text(text: str, max_len: int = 300) -> str:
    """Scrubs API keys, bearer tokens, and credentials from upstream error responses."""
    if text is None:
        return ""
    text_str = str(text)
    # Redact bearer tokens
    s = re.sub(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.]{8,}", "Bearer [REDACTED]", text_str)
    # Redact key / secret / password assignments
    s = re.sub(
        r"(?i)\b([a-z0-9_]*(?:key|secret|password|token))\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{8,}[\"']?",
        r"\1=[REDACTED]",
        s,
    )
    # Redact authorization header patterns
    s = re.sub(r"(?i)authorization\s*:\s*[^\s,]+", "Authorization: [REDACTED]", s)
    # Redact bare API keys and tokens (sk-proj, sk-ant, sk-, AKIA, AIza)
    s = re.sub(r"\bsk-proj-[A-Za-z0-9_\-]{10,}", "[REDACTED_API_KEY]", s)
    s = re.sub(r"\bsk-ant-[A-Za-z0-9_\-]{10,}", "[REDACTED_API_KEY]", s)
    s = re.sub(r"\bsk-[A-Za-z0-9_\-]{20,}", "[REDACTED_API_KEY]", s)
    s = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]", s)
    s = re.sub(r"\bAIza[0-9A-Za-z_\-]{30,}\b", "[REDACTED_GOOGLE_KEY]", s)
    return s[:max_len]


def _check_ip_allowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> tuple[bool, str]:
    if ip.is_unspecified:
        return False, f"wildcard address {ip} not allowed in offline mode"
    if ip in BANNED_METADATA_IPS:
        return False, f"cloud metadata address {ip} not allowed in offline mode"
    if ip.is_loopback:
        return True, "loopback IP"
    if ip.is_private:
        return True, "private network IP"
    if ip.is_link_local:
        return True, "link-local IP"
    return False, f"public IP address {ip} not allowed in offline mode"


def is_offline_host(
    raw_url_or_host: str, extra_allowed: list[str] | None = None
) -> tuple[bool, str]:
    """Validates that a model endpoint host is permissible in offline mode.

    Permissible: loopback, RFC 1918 private IPv4, fc00::/7 private IPv6, link-local,
    or a host explicitly listed in extra_allowed (offline_allowed_hosts).
    Wildcard addresses (0.0.0.0, ::) and cloud metadata addresses are forbidden.
    """
    ok, reason, _, _ = validate_and_pin_offline_host(raw_url_or_host, extra_allowed)
    return ok, reason


def validate_and_pin_offline_host(
    raw_url_or_host: str, extra_allowed: list[str] | None = None
) -> tuple[bool, str, str, str | None]:
    """Validates that a host is allowed in offline mode using a single DNS resolution check,
    and returns (is_allowed, reason, host, pinned_ip)."""
    extra = {h.strip().strip("[]").lower() for h in (extra_allowed or []) if h.strip()}
    host = raw_url_or_host.strip()
    if "://" in host:
        parsed = urlparse(host)
        host = parsed.hostname or ""
    elif ":" in host:
        # host:port (handle IPv6 brackets)
        if host.startswith("[") and "]" in host:
            host = host.split("]")[0].lstrip("[")
        else:
            host = host.split(":")[0]

    host = host.strip("[]").lower()
    if not host:
        return False, "empty host", "", None

    if host in ("localhost", "127.0.0.1", "::1"):
        pin_ip = "127.0.0.1" if host != "::1" else "::1"
        return True, "loopback", host, pin_ip

    # Check IP literal
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None:
        if ip.is_unspecified:
            return False, f"wildcard address {ip} not allowed in offline mode", host, None
        if ip in BANNED_METADATA_IPS:
            return False, f"cloud metadata address {ip} not allowed in offline mode", host, None

        if host in extra:
            return True, f"admin allowed host: {host}", host, str(ip)

        ok, reason = _check_ip_allowed(ip)
        if not ok:
            return False, reason, host, None
        return True, reason, host, str(ip)

    if host in extra:
        # Hostname is explicitly permitted by admin. Try to resolve and verify resolved IPs if resolvable.
        try:
            addrinfo = socket.getaddrinfo(host, None)
            pinned_ip = addrinfo[0][4][0] if addrinfo else None
            for info in addrinfo:
                ip_str = info[4][0]
                try:
                    res_ip = ipaddress.ip_address(ip_str)
                    if res_ip.is_unspecified:
                        return False, f"allowed host '{host}' resolves to forbidden wildcard IP {ip_str}", host, None
                    if res_ip in BANNED_METADATA_IPS:
                        return False, f"allowed host '{host}' resolves to forbidden metadata IP {ip_str}", host, None
                except ValueError:
                    pass
        except Exception:  # noqa: BLE001
            pinned_ip = None
        return True, f"admin allowed host: {host}", host, pinned_ip

    # Single DNS resolution check
    try:
        addrinfo = socket.getaddrinfo(host, None)
        if not addrinfo:
            return False, f"could not resolve host '{host}'", host, None
        pinned_ip = addrinfo[0][4][0]
        for info in addrinfo:
            ip_str = info[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                return False, f"invalid IP {ip_str} for host '{host}'", host, None
            ok, reason = _check_ip_allowed(ip)
            if not ok:
                return False, f"host '{host}' resolves to forbidden IP {ip_str}: {reason}", host, None
        return True, f"private host: {host}", host, pinned_ip
    except (socket.gaierror, OSError) as e:
        return False, f"hostname '{host}' resolution failed: {e}", host, None


def models_match(requested: str, served: str) -> bool:
    """Compares requested and served model strings, accounting for provider prefixes.

    Does not strip -vN, size, or variant suffixes so distinct model versions/sizes warn.
    Matches when served is requested plus only a date or build suffix
    (-YYYY-MM-DD, -YYYYMMDD, -NNN, :latest).
    Returns False if either string is empty.
    """
    if not served or not requested:
        return False
    req = requested.lower().strip()
    srv = served.lower().strip()
    if not req or not srv:
        return False
    if req == srv:
        return True

    # Strip provider/region prefixes (e.g. Bedrock prefixes, Vertex publisher prefix)
    prefixes = (
        "us.anthropic.",
        "eu.anthropic.",
        "apac.anthropic.",
        "anthropic.",
        "us.",
        "eu.",
        "apac.",
        "publishers/google/models/",
    )
    for p in prefixes:
        req = req.removeprefix(p)
        srv = srv.removeprefix(p)

    if req == srv:
        return True

    # AWS Bedrock model IDs append an invocation revision like :0 or :1, and Bedrock Anthropic IDs append -vN:0
    req_sub = re.sub(r"-v\d+:\d+$", "", req)
    srv_sub = re.sub(r"-v\d+:\d+$", "", srv)
    req_sub = re.sub(r":\d+$", "", req_sub)
    srv_sub = re.sub(r":\d+$", "", srv_sub)
    if req_sub == srv_sub:
        return True

    # Date or build suffix: -YYYY-MM-DD, -YYYYMMDD, -NNN, :latest
    # Match when served name is requested plus only a date or build suffix (never in reverse)
    date_or_build = re.compile(r"(-\d{4}-\d{2}-\d{2}|-\d{8}|-\d{3}|:latest)$")
    return bool(date_or_build.sub("", srv_sub) == req_sub)


class PinnedSyncBackend(httpcore.SyncBackend):
    """Network backend that connects to a pre-validated IP address for a specific host,
    defeating DNS rebinding attacks while keeping the original Host header and TLS SNI."""

    def __init__(self, pinned_host: str, pinned_ip: str):
        super().__init__()
        self.pinned_host = pinned_host.lower()
        self.pinned_ip = pinned_ip

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any = None,
    ) -> httpcore.NetworkStream:
        target = self.pinned_ip if host.lower() == self.pinned_host else host
        return super().connect_tcp(
            target,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class PinnedHTTPTransport(httpx.HTTPTransport):
    """HTTP transport pinning connections for a specific hostname to a checked IP address,
    with trust_env disabled to prevent proxy bypass, preserving SSL context, limits, and retry options."""

    def __init__(
        self,
        pinned_host: str,
        pinned_ip: str,
        *,
        verify: Any = True,
        cert: Any = None,
        http1: bool = True,
        http2: bool = False,
        limits: httpx.Limits | None = None,
        retries: int = 0,
        socket_options: Any = None,
        **kwargs: Any,
    ):
        from httpx._config import create_ssl_context

        limits_obj = limits or httpx.Limits()
        kwargs["trust_env"] = False
        super().__init__(
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            limits=limits_obj,
            retries=retries,
            socket_options=socket_options,
            **kwargs,
        )
        ssl_ctx = create_ssl_context(verify=verify, cert=cert, trust_env=False)
        self._pool = httpcore.ConnectionPool(
            ssl_context=ssl_ctx,
            max_connections=limits_obj.max_connections,
            max_keepalive_connections=limits_obj.max_keepalive_connections,
            keepalive_expiry=limits_obj.keepalive_expiry,
            http1=http1,
            http2=http2,
            retries=retries,
            socket_options=socket_options,
            network_backend=PinnedSyncBackend(pinned_host, pinned_ip),
        )


def build_offline_transport(
    raw_url: str,
    extra_allowed: list[str] | None = None,
    *,
    verify: Any = True,
    limits: httpx.Limits | None = None,
    retries: int = 0,
    http2: bool = False,
) -> tuple[httpx.BaseTransport | None, str | None]:
    """Validates host for offline usage with a single DNS lookup and builds a pinned transport to defeat DNS rebinding.
    Returns (transport, error_reason)."""
    ok, reason, host, pinned_ip = validate_and_pin_offline_host(raw_url, extra_allowed)
    if not ok:
        return None, reason
    if pinned_ip is None:
        return httpx.HTTPTransport(trust_env=False), reason
    return PinnedHTTPTransport(
        host,
        pinned_ip,
        verify=verify,
        limits=limits,
        retries=retries,
        http2=http2,
    ), reason
