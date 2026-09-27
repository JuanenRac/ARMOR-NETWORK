"""Readers of the text the operating system's network tools print, and of the small messages of NetBIOS and SSDP: pure functions, tested with real samples.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

The tools speak the language of the system (`ipconfig` in Spanish says "Máscara de subred"), so nothing here looks for a word: it looks for what the value looks like (an
address, a mask, a MAC) and where it is (the line after another, inside the block of an adapter).
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field

from .ipnet import is_mask
from .oui import normalize_mac

IP_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d.])")
MAC_RE = re.compile(r"(?<![0-9A-Fa-f])([0-9A-Fa-f]{2}(?:[:\-][0-9A-Fa-f]{2}){5})(?![0-9A-Fa-f])")


@dataclass
class Adapter:
    name: str
    ips: list[str] = field(default_factory=list)
    masks: dict[str, str] = field(default_factory=dict)     # ip -> mask
    mac: str | None = None
    gateway: str | None = None


def parse_ipconfig(text: str) -> list[Adapter]:
    """`ipconfig /all` (any language): one adapter per unindented header that ends in a colon. In a block the addresses come in an order the system keeps: an address, then its
    mask, then (after the lease dates) the default gateway, then the DHCP and DNS servers. So a mask belongs to the address before it, and the first address that is not a mask
    after a mask is the gateway. The first MAC in the block is the adapter's own."""
    adapters: list[Adapter] = []
    current: Adapter | None = None
    last_ip: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not line[0].isspace() and stripped.endswith(":"):
            current, last_ip = Adapter(name=stripped[:-1][:64]), None
            adapters.append(current)
            continue
        if current is None:
            continue
        mac = MAC_RE.search(stripped)
        if mac and current.mac is None:
            current.mac = normalize_mac(mac.group(1))
        for candidate in IP_RE.findall(stripped):
            if candidate == "0.0.0.0":
                continue
            if is_mask(candidate):
                if last_ip is not None:
                    current.masks.setdefault(last_ip, candidate)
            elif last_ip is not None and last_ip in current.masks:
                if current.gateway is None:
                    current.gateway = candidate
            else:
                current.ips.append(candidate)
                last_ip = candidate
    return adapters


def parse_route_windows(text: str) -> tuple[str, str] | None:
    """`route print -4`: the default route with the lowest metric as (gateway, the address of the interface it leaves by)."""
    best: tuple[int, str, str] | None = None
    for line in text.splitlines():
        columns = line.split()
        if len(columns) >= 5 and columns[0] == "0.0.0.0" and columns[1] == "0.0.0.0" and IP_RE.fullmatch(columns[2]) and IP_RE.fullmatch(columns[3]) and columns[4].isdigit():
            metric = int(columns[4])
            if best is None or metric < best[0]:
                best = (metric, columns[2], columns[3])
    return (best[1], best[2]) if best else None


def parse_ip_route(text: str) -> tuple[str, str | None] | None:
    """`ip route show default`: `default via 192.168.0.1 dev eth0 ...` as (gateway, interface name)."""
    for line in text.splitlines():
        columns = line.split()
        if columns[:1] == ["default"] and "via" in columns:
            gateway = columns[columns.index("via") + 1]
            device = columns[columns.index("dev") + 1] if "dev" in columns else None
            return gateway, device
    return None


def parse_ip_addr(text: str) -> list[tuple[str, str]]:
    """`ip -o -4 addr show`: (interface, address/prefix) per line."""
    found = []
    for line in text.splitlines():
        match = re.search(r"^\d+:\s+(\S+)\s+inet\s+(\d+\.\d+\.\d+\.\d+/\d+)", line.strip())
        if match:
            found.append((match.group(1), match.group(2)))
    return found


def parse_ping(text: str) -> tuple[float, int | None] | None:
    """One reply of `ping` (Windows or Linux, any language) as (milliseconds, TTL); None when there was no reply. A time of "<1ms" is 0.5."""
    ttl_match = re.search(r"\bttl[=:]\s*(\d+)", text, re.I)
    if ttl_match is None:
        return None
    time_match = re.search(r"(?:time|tiempo|temps|zeit|tempo)\s*([=<])\s*(\d+(?:[.,]\d+)?)\s*ms", text, re.I)
    if time_match is None:
        return None
    value = float(time_match.group(2).replace(",", "."))
    if time_match.group(1) == "<":
        value = min(value, 0.5)
    return value, int(ttl_match.group(1))


def parse_netstat_e(text: str) -> tuple[int, int] | None:
    """`netstat -e` of Windows: the line of the bytes, a word and two big numbers (received, sent), whatever the language."""
    for line in text.splitlines():
        match = re.match(r"^\s*[^\W\d_]+\s+(\d{3,})\s+(\d{3,})\s*$", line)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def parse_proc_net_dev(text: str, interface: str | None = None) -> tuple[int, int] | None:
    """`/proc/net/dev`: (received, sent) bytes of one interface, or of all but the loopback."""
    rx = tx = 0
    found = False
    for line in text.splitlines()[2:]:
        name, _, rest = line.partition(":")
        name = name.strip()
        columns = rest.split()
        if len(columns) < 9 or (interface is None and name == "lo") or (interface is not None and name != interface):
            continue
        rx += int(columns[0])
        tx += int(columns[8])
        found = True
    return (rx, tx) if found else None


# ---- NetBIOS: the name a Windows machine or a Samba server gives itself ----------------------------------------------------------------------
def nbstat_query(transaction: int = 0x4152) -> bytes:
    """A node-status request to UDP 137 for the name `*`: the machine answers with the names it has."""
    name = b"CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"      # "*" padded with zeros, first-level encoded
    return struct.pack(">HHHHHH", transaction, 0, 1, 0, 0, 0) + b"\x20" + name + b"\x00" + struct.pack(">HH", 0x0021, 1)


def parse_nbstat(data: bytes) -> str | None:
    """The machine's own name in a node-status answer (the first unique name), or None."""
    if len(data) < 57:
        return None
    position = 12
    if data[position] != 0x20:
        return None
    position += 1 + 32 + 1                 # the echoed name
    position += 2 + 2 + 4 + 2              # type, class, ttl, data length
    if position >= len(data):
        return None
    count = data[position]
    position += 1
    for _ in range(count):
        if position + 18 > len(data):
            return None
        raw, flags = data[position:position + 15], struct.unpack(">H", data[position + 16:position + 18])[0]
        position += 18
        if not flags & 0x8000:              # a unique name, not a group
            name = raw.decode("ascii", "replace").strip()
            if name and name.isprintable():
                return name[:63]
    return None


# ---- SSDP / UPnP ---------------------------------------------------------------------------------------------------------------------------------
def parse_ssdp_response(data: bytes) -> dict[str, str]:
    """The headers of a reply to an M-SEARCH (upper-case names): ST, USN, LOCATION, SERVER."""
    text = data.decode("utf-8", "replace")
    lines = text.split("\r\n")
    if not lines or not lines[0].upper().startswith(("HTTP/1.1 200", "NOTIFY")):
        return {}
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if sep:
            headers[name.strip().upper()] = value.strip()[:200]
    return headers


def upnp_device_info(xml: str) -> dict[str, str]:
    """friendlyName, manufacturer and modelName of a UPnP device description (read with patterns: the file comes from any device, so it is never parsed as XML)."""
    info = {}
    for tag in ("friendlyName", "manufacturer", "modelName"):
        match = re.search(rf"<{tag}>\s*([^<]{{1,80}})\s*</{tag}>", xml)
        if match:
            info[tag] = " ".join(match.group(1).split())
    return info


def ssdp_service(st: str) -> str | None:
    """`urn:schemas-upnp-org:device:MediaRenderer:1` -> `MediaRenderer`; None for the generic answers."""
    if st in ("upnp:rootdevice", "ssdp:all") or st.startswith("uuid:"):
        return None
    parts = st.split(":")
    if len(parts) >= 5 and parts[0] == "urn" and parts[2] in ("device", "service"):
        return parts[3][:48]
    return st[:48] or None
