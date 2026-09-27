"""The neighbour table of the machine: which MAC answers for which IP on the local network.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

It is what the operating system already learned by talking to the neighbours (`arp -a` on Windows, `/proc/net/arp` or `ip neigh` on Linux), so reading it sends nothing.
The parsers find an address and a MAC on a line whatever the language of the system: they do not look at the words.
"""

from __future__ import annotations

import re

from .ipnet import is_private_address
from .oui import is_unicast, normalize_mac

IP_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
MAC_ANY = re.compile(r"\b([0-9A-Fa-f]{2}(?:[:\-][0-9A-Fa-f]{2}){5})\b")


def _pair(ip: str, mac_text: str, table: dict[str, str], within: str | None) -> None:
    mac = normalize_mac(mac_text)
    if mac is None or not is_unicast(mac) or mac == "00:00:00:00:00:00" or not is_private_address(ip):
        return
    if within is not None and not is_private_address(within):
        return
    table[ip] = mac


def parse_arp_windows(text: str) -> dict[str, str]:
    """`arp -a` of Windows (in any language): a block per interface, a line per neighbour with the address, the MAC and the kind (static, dynamic)."""
    table: dict[str, str] = {}
    for line in text.splitlines():
        ip = IP_RE.search(line)
        mac = MAC_ANY.search(line)
        if ip and mac:
            _pair(ip.group(1), mac.group(1), table, None)
    return table


def parse_proc_net_arp(text: str) -> dict[str, str]:
    """`/proc/net/arp`: `IP address  HW type  Flags  HW address  Mask  Device`; a flag of 0x0 is an entry that never resolved."""
    table: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        columns = line.split()
        if len(columns) >= 4 and columns[2] != "0x0":
            _pair(columns[0], columns[3], table, None)
    return table


def parse_ip_neigh(text: str) -> dict[str, str]:
    """`ip neigh`: `192.168.0.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE`; FAILED and INCOMPLETE entries have no address."""
    table: dict[str, str] = {}
    for line in text.splitlines():
        if "FAILED" in line or "INCOMPLETE" in line:
            continue
        ip = IP_RE.search(line)
        mac = MAC_ANY.search(line)
        if ip and mac:
            _pair(ip.group(1), mac.group(1), table, None)
    return table


def in_network(table: dict[str, str], cidr: str) -> dict[str, str]:
    """Only the neighbours that are inside the network being watched (the table also holds the ones of other interfaces)."""
    import ipaddress

    network = ipaddress.ip_network(cidr, strict=False)
    return {ip: mac for ip, mac in table.items() if ipaddress.ip_address(ip) in network}
