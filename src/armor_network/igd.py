"""The traffic counters of the router, asked of it as a UPnP Internet Gateway Device: no login, nothing written.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Many routers answer, to anyone on the network, how many bytes they have carried (`GetTotalBytesReceived`, `GetTotalBytesSent` of the service `WANCommonInterfaceConfig`). It needs no
credential and changes nothing; it is OPT-IN (`router_igd` in the settings, off by default). The router is the one the node already knows is the gateway, the address of its description
comes from the SSDP answer the discovery already reads, and only a private address is ever asked. This module builds the questions and reads the answers (with patterns, never as XML:
the text comes from a device); the HTTP is done by the caller with `ask`.

What it does NOT do: log in, read the leases or the names of the devices (that needs the router's credentials: TR-064 or the OpenWrt interface, a later option with a stored credential).
"""
from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

from .ipnet import is_private_address

SERVICE_TYPES = ("urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1",)
MAX_COUNTER = 2 ** 64
ACTIONS = ("GetTotalBytesReceived", "GetTotalBytesSent")


def control_url(description: str, location: str) -> str | None:
    """The address to send the questions to, from the device description at `location`, or None when the router has no such service or the address is not on the local network."""
    for service in SERVICE_TYPES:
        match = re.search(rf"<serviceType>\s*{re.escape(service)}\s*</serviceType>.*?<controlURL>\s*([^<\s]{{1,200}})\s*</controlURL>", description, re.S)
        if match:
            url = urljoin(location, match.group(1))
            parts = urlparse(url)
            host = parts.hostname or ""
            if parts.scheme == "http" and is_private_address(host) and urlparse(location).hostname == host:
                return url
    return None


def soap_body(action: str, service: str = SERVICE_TYPES[0]) -> bytes:
    """The SOAP envelope of an action without arguments."""
    if action not in ACTIONS:
        raise ValueError(f"{action!r} is not one of the read-only actions")
    return (f'<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{action} xmlns:u="{service}"/></s:Body></s:Envelope>').encode("ascii")


def soap_headers(action: str, service: str = SERVICE_TYPES[0]) -> dict[str, str]:
    if action not in ACTIONS:
        raise ValueError(f"{action!r} is not one of the read-only actions")
    return {"Content-Type": 'text/xml; charset="utf-8"', "SOAPAction": f'"{service}#{action}"'}


def parse_counter(action: str, response: str) -> int | None:
    """The number in the answer to an action (`NewTotalBytesReceived` or `NewTotalBytesSent`), or None when it is not a plain unsigned number."""
    name = {"GetTotalBytesReceived": "NewTotalBytesReceived", "GetTotalBytesSent": "NewTotalBytesSent"}.get(action)
    if name is None:
        return None
    match = re.search(rf"<{name}>\s*(\d{{1,20}})\s*</{name}>", response)
    if not match:
        return None
    value = int(match.group(1))
    return value if value < MAX_COUNTER else None


def read_totals(url: str, ask: Callable[[str, bytes, dict[str, str]], str | None]) -> tuple[int, int] | None:
    """(bytes received, bytes sent) by the router since it started, or None when it does not answer both. `ask(url, body, headers)` does the HTTP request and returns the text of the answer."""
    values = []
    for action in ACTIONS:
        text = ask(url, soap_body(action), soap_headers(action))
        value = parse_counter(action, text) if text else None
        if value is None:
            return None
        values.append(value)
    return values[0], values[1]


class RateMeter:
    """From the totals of the router at two moments to bytes per second; a counter that goes down (the router restarted or the counter wrapped) restarts the measure instead of giving a huge number."""

    def __init__(self) -> None:
        self._last: tuple[float, int, int] | None = None

    def update(self, now_s: float, received: int, sent: int) -> tuple[float, float] | None:
        last, self._last = self._last, (now_s, received, sent)
        if last is None or now_s <= last[0] or received < last[1] or sent < last[2]:
            return None
        elapsed = now_s - last[0]
        return (received - last[1]) / elapsed, (sent - last[2]) / elapsed
