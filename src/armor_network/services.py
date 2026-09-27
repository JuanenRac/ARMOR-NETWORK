"""What the open ports, the announced services and the maker of a device say about it: names for ports, cleaned banners, and the guesses (kind, operating system).

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Every result of this module is a GUESS and is called one in the message: a device with port 554 open is very probably a camera, and a device with 22 and 80 open is probably a
server, and both may be something else. Nothing here connects to anything; the scanning is in `system_io.py`.
"""

from __future__ import annotations

import re

SERVICE_NAMES: dict[int, str] = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 80: "http", 110: "pop3", 139: "netbios", 143: "imap", 443: "https", 445: "smb", 502: "modbus",
    515: "lpd", 554: "rtsp", 631: "ipp", 993: "imaps", 1880: "node-red", 1883: "mqtt", 2049: "nfs", 3000: "http-alt", 3306: "mysql", 3389: "rdp", 4840: "opc-ua",
    5000: "http-alt", 5001: "https-alt", 5432: "postgres", 5900: "vnc", 6379: "redis", 7547: "tr-069", 8000: "http-alt", 8008: "cast", 8009: "cast", 8080: "http-alt",
    8081: "http-alt", 8443: "https-alt", 8554: "rtsp-alt", 8883: "mqtt-tls", 9000: "http-alt", 9100: "jetdirect", 18080: "armor-server", 18081: "armor-studio",
    32400: "plex", 34567: "dvr", 37777: "dahua",
}
# The ports a quick look tries, then the ones a normal look adds. Chosen for what a house has: routers, cameras, printers, NAS, TVs, smart devices, computers.
PORTS_QUICK: tuple[int, ...] = (22, 23, 53, 80, 139, 443, 445, 554, 631, 1883, 3389, 5000, 8000, 8008, 8080, 9100, 37777)
PORTS_STANDARD: tuple[int, ...] = tuple(sorted(set(PORTS_QUICK) | {21, 25, 110, 143, 502, 515, 993, 1880, 2049, 3000, 3306, 4840, 5001, 5432, 5900, 6379, 7547, 8009, 8081, 8443,
                                                                   8554, 8883, 9000, 18080, 18081, 32400, 34567}))
PROFILES = {"quick": PORTS_QUICK, "standard": PORTS_STANDARD}
# Open ports that a house rarely wants open on a device that anyone on the network can reach: an old remote shell, an unencrypted file transfer, a remote desktop, a database.
RISKY_PORTS = frozenset({21, 23, 3389, 5900, 6379, 3306, 5432, 7547, 445})


def service_name(port: int) -> str | None:
    return SERVICE_NAMES.get(port)


def clean_banner(raw: bytes | str, limit: int = 80) -> str | None:
    """The first line of what a service said, made safe to keep and show: printable characters only, spaces collapsed, cut at `limit`. None when nothing readable is left."""
    text = raw if isinstance(raw, str) else raw.decode("utf-8", "replace")
    text = text.replace("\r", "\n").split("\n", 1)[0]
    text = "".join(ch if ch.isprintable() and ch != "\ufffd" else " " for ch in text)      # bytes that are not text (a Telnet negotiation) leave nothing behind
    text = " ".join(text.split())
    if not text:
        return None
    return text[:limit].rstrip()


_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_SERVER = re.compile(r"^server:\s*(.+)$", re.I | re.M)


def parse_http(raw: bytes) -> str | None:
    """The `Server` header and the page title of a web answer, joined ("nginx/1.24; Router login"), or None when it is not a web answer."""
    text = raw.decode("latin-1", "replace")
    if not text.startswith("HTTP/"):
        return None
    server = _SERVER.search(text)
    title = _TITLE.search(text)
    parts = []
    if server:
        parts.append(" ".join(server.group(1).split()))
    if title:
        parts.append(" ".join(re.sub(r"<[^>]+>", " ", title.group(1)).split()))
    return clean_banner("; ".join(part for part in parts if part)) if parts else clean_banner(text.splitlines()[0])


def guess_os(ttl: int | None) -> str | None:
    """From the TTL a reply arrived with. On the same network no hop has lowered it, so it is the initial value of the sender: 64 for Linux, Android and Apple, 128 for Windows, 255 for network equipment."""
    if ttl is None or ttl <= 0:
        return None
    if ttl <= 64:
        return "Linux, Android or Apple"
    if ttl <= 128:
        return "Windows"
    return "network equipment"


_VENDOR_KINDS = (
    ("camera", ("hikvision", "dahua", "reolink", "amcrest", "axis communications", "foscam", "wyze", "eufy", "ezviz", "annke", "uniview")),
    ("printer", ("brother", "canon", "epson", "lexmark", "xerox", "kyocera", "ricoh", "konica", "hewlett", "hp inc")),
    ("tv", ("roku", "vizio", "tcl", "hisense", "sonos", "nvidia shield")),
    ("nas", ("synology", "qnap", "western digital", "asustor", "terramaster")),
    ("iot", ("espressif", "tuya", "shelly", "allterco", "itead", "sonoff", "ecobee", "nest labs", "philips lighting", "signify", "tp-link smart", "shenzhen", "hangzhou", "zhejiang")),
    ("network", ("ubiquiti", "netgear", "cisco", "mikrotik", "routerboard", "zyxel", "d-link", "tp-link", "tp link", "aruba", "juniper", "engenius", "linksys", "huawei", "sagemcom",
                 "zte", "arris", "technicolor", "compal", "askey", "fritz", "avm")),
    ("computer", ("raspberry", "intel corporate", "dell", "lenovo", "microsoft", "asustek", "gigabyte", "micro-star", "msi", "vmware", "hyper-v", "realtek")),
)
_SERVICE_KINDS = (
    ("tv", ("_googlecast._tcp", "_roku", "_spotify-connect._tcp", "urn:dial-multiscreen-org:service:dial", "mediarenderer")),
    ("printer", ("_ipp._tcp", "_printer._tcp", "_pdl-datastream._tcp", "_scanner._tcp", "printer")),
    ("iot", ("_hap._tcp", "_homekit._tcp", "_hue._tcp", "_shelly._tcp", "_esphomelib._tcp", "_mqtt._tcp", "_matter._tcp")),
    ("computer", ("_workstation._tcp", "_smb._tcp", "_device-info._tcp", "_rdp._tcp")),
)
_NAME_KINDS = (
    ("phone", ("iphone", "ipad", "android", "galaxy", "pixel", "redmi", "oneplus", "huawei-p", "oppo")),
    ("computer", ("macbook", "imac", "desktop", "laptop", "pc-", "-pc", "windows", "ubuntu", "thinkpad", "surface")),
    ("tv", ("tv", "chromecast", "roku", "bravia", "firetv", "appletv")),
    ("printer", ("printer", "epson", "canon", "brother", "laserjet")),
    ("camera", ("cam", "ipcam", "hikvision", "dahua")),
    ("nas", ("nas", "synology", "diskstation")),
)


def guess_kind(*, is_gateway: bool = False, ports: set[int] | frozenset[int] = frozenset(), services: list[str] | tuple[str, ...] = (), vendor: str | None = None,
               hostname: str | None = None, randomized: bool = False) -> str:
    """One of the kinds of the contract. Order matters: the router first, then what a device does (its ports and announcements), then who made it, then what it is called."""
    if is_gateway:
        return "router"
    if ports & {554, 8554, 37777, 34567}:
        return "camera"
    if ports & {9100, 515, 631}:
        return "printer"
    lowered_services = " ".join(services).lower()
    for kind, words in _SERVICE_KINDS:
        if any(word in lowered_services for word in words):
            return kind
    if ports & {8008, 8009}:
        return "tv"
    if ports & {32400, 2049}:
        return "nas"
    name = (hostname or "").lower()
    maker = (vendor or "").lower()
    for kind, words in _VENDOR_KINDS:
        if maker and any(word in maker for word in words):
            if kind == "computer" and name and any(w in name for w in ("iphone", "ipad", "android")):
                break
            return kind
    if maker and "apple" in maker:
        for kind, words in _NAME_KINDS:
            if kind in ("phone", "computer", "tv") and any(word in name for word in words):
                return kind
        return "phone" if not ports else "computer"
    if ports & {1883, 8883, 1880, 502, 4840}:
        return "iot" if not ports & {22, 445, 3389} else "server"
    for kind, words in _NAME_KINDS:
        if name and any(word in name for word in words):
            return kind
    if ports & {3389, 445, 139}:
        return "computer"
    if ports & {22, 3306, 5432, 6379, 8080, 8000, 3000, 18080}:
        return "server"
    if randomized and not ports:
        return "phone"
    if ports & {80, 443}:
        return "iot" if maker and any(word in maker for word in ("espressif", "tuya", "shelly")) else "unknown"
    return "unknown"


def risky_open_ports(ports: set[int] | frozenset[int]) -> list[int]:
    return sorted(ports & RISKY_PORTS)
