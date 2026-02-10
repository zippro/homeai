from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_external_http_url(url: str) -> None:
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise ValueError("image_url_invalid_scheme")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError("image_url_missing_host")
    if hostname in _BLOCKED_HOSTS or hostname.endswith(".local"):
        raise ValueError("image_url_blocked_host")

    try:
        _assert_public_ip(ipaddress.ip_address(hostname))
        return
    except ValueError:
        pass

    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except OSError as exc:
        raise ValueError(f"image_url_dns_resolution_failed:{exc}") from exc

    if not addr_info:
        raise ValueError("image_url_dns_resolution_failed:no_records")

    for entry in addr_info:
        ip_raw = entry[4][0]
        ip_value = ip_raw.split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(ip_value)
        except ValueError as exc:
            raise ValueError(f"image_url_invalid_resolved_ip:{ip_raw}") from exc
        _assert_public_ip(ip)


def _assert_public_ip(ip: ipaddress._BaseAddress) -> None:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or any(ip in network for network in _BLOCKED_NETWORKS)
    ):
        raise ValueError("image_url_non_public_target")
