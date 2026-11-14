"""Finding a DHCP server that should not be there: the question to put on the network and the reading of the answers.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

A second DHCP server on the network (a router somebody plugged in, or an attacker's) hands out wrong gateways and DNS servers. The check is one DHCPDISCOVER sent once to the broadcast
address, with a random transaction number and the address of this node's own network card, and every DHCPOFFER that comes back in a few seconds is read: the offers do not give the
addresses anything and the node never answers them with a request, so no address is taken. It is OPT-IN (`rogue_dhcp` in the settings, off by default) because it puts one broadcast
packet on the network. This module only builds and reads packets (nothing here opens a socket); the sending is in `system_io.py`.
"""
from __future__ import annotations

import ipaddress
import struct

MAGIC_COOKIE = b"\x63\x82\x53\x63"
SERVER_PORT, CLIENT_PORT = 67, 68
OPT_PAD, OPT_END, OPT_ROUTER, OPT_DNS, OPT_LEASE, OPT_TYPE, OPT_SERVER_ID, OPT_PARAMETERS = 0, 255, 3, 6, 51, 53, 54, 55
DISCOVER, OFFER = 1, 2
MAX_OFFERS = 16


def build_discover(mac: bytes, xid: int) -> bytes:
    """A DHCPDISCOVER for a hardware address of six bytes and a transaction number: the broadcast flag is set so that the answers can be read without owning an address."""
    if len(mac) != 6:
        raise ValueError("a hardware address is six bytes")
    if not 0 <= xid <= 0xFFFFFFFF:
        raise ValueError("a transaction number is 32 bits")
    header = struct.pack("!BBBBIHH4s4s4s4s16s64s128s", 1, 1, 6, 0, xid, 0, 0x8000, b"\0" * 4, b"\0" * 4, b"\0" * 4, b"\0" * 4, mac + b"\0" * 10, b"\0" * 64, b"\0" * 128)
    options = bytes([OPT_TYPE, 1, DISCOVER, OPT_PARAMETERS, 3, OPT_ROUTER, OPT_DNS, OPT_LEASE, OPT_END])
    return header + MAGIC_COOKIE + options


def _options(data: bytes) -> dict[int, bytes] | None:
    found: dict[int, bytes] = {}
    index = 0
    while index < len(data):
        code = data[index]
        if code == OPT_END:
            return found
        if code == OPT_PAD:
            index += 1
            continue
        if index + 1 >= len(data):
            return None
        length = data[index + 1]
        if index + 2 + length > len(data):
            return None
        found.setdefault(code, data[index + 2:index + 2 + length])
        index += 2 + length
    return found


def parse_offer(packet: bytes, xid: int) -> dict | None:
    """The reading of one DHCPOFFER answering our transaction: {"server", "offered", "router", "dns", "lease_s"}; None for anything that is not a well-formed offer to us."""
    if len(packet) < 240 or packet[0] != 2 or packet[236:240] != MAGIC_COOKIE:
        return None
    if struct.unpack("!I", packet[4:8])[0] != xid:
        return None
    options = _options(packet[240:])
    if not options or options.get(OPT_TYPE) != bytes([OFFER]):
        return None
    server = options.get(OPT_SERVER_ID)
    if server is None or len(server) != 4:
        return None
    reading: dict = {"server": str(ipaddress.IPv4Address(server)), "offered": str(ipaddress.IPv4Address(packet[16:20]))}
    router = options.get(OPT_ROUTER)
    if router and len(router) >= 4:
        reading["router"] = str(ipaddress.IPv4Address(router[:4]))
    dns = options.get(OPT_DNS)
    if dns and len(dns) % 4 == 0:
        reading["dns"] = [str(ipaddress.IPv4Address(dns[i:i + 4])) for i in range(0, min(len(dns), 16), 4)]
    lease = options.get(OPT_LEASE)
    if lease and len(lease) == 4:
        reading["lease_s"] = struct.unpack("!I", lease)[0]
    return reading


def judge(offers: list[dict], allowed: set[str]) -> list[dict]:
    """The findings in a list of offers: one for every server that is not in `allowed` (the address of the gateway and the servers the person named), once per server, at most `MAX_OFFERS`.

    {"kind": "rogue_dhcp", "server": ..., "offered": ..., "router": ..., "dns": [...]} """
    found: list[dict] = []
    seen: set[str] = set()
    for offer in offers[:MAX_OFFERS]:
        server = offer.get("server")
        if not isinstance(server, str) or server in allowed or server in seen:
            continue
        seen.add(server)
        finding = {"kind": "rogue_dhcp", "server": server, "offered": offer.get("offered")}
        for name in ("router", "dns"):
            if name in offer:
                finding[name] = offer[name]
        found.append(finding)
    return found
