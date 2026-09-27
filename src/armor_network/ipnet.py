"""Addresses and the rule that keeps this program on the owner's own network.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

ARMOR-NETWORK looks at the network it is plugged into and nothing else: it refuses to scan an address that is not in a private range (RFC 1918), and no more than a
/22 (1024 addresses) at a time. That is a guard, not an option: the one place that decides what may be probed is `check_scan_range`.
"""

from __future__ import annotations

import ipaddress

PRIVATE_RANGES = tuple(ipaddress.ip_network(net) for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
MAX_HOSTS = 1024


class ScanRefused(ValueError):
    """The address or range is not one this program may probe."""


def is_private_address(text: str) -> bool:
    """True for a unicast address inside 10/8, 172.16/12 or 192.168/16."""
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    return address.version == 4 and any(address in net for net in PRIVATE_RANGES) and not address.is_multicast


def check_scan_range(cidr: str) -> ipaddress.IPv4Network:
    """The network to scan, or `ScanRefused`: it must be IPv4, inside a private range and at most 1024 addresses."""
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError as error:
        raise ScanRefused(f"{cidr!r} is not a network") from error
    if network.version != 4:
        raise ScanRefused("only IPv4 networks are scanned")
    if not any(network.subnet_of(private) for private in PRIVATE_RANGES):
        raise ScanRefused(f"{network} is not a private network: this program only looks at the network it is connected to")
    if network.num_addresses > MAX_HOSTS:
        raise ScanRefused(f"{network} has {network.num_addresses} addresses; at most {MAX_HOSTS} (a /22) are scanned")
    if network.prefixlen > 30:
        raise ScanRefused(f"{network} is too small to be a network")
    return network


def hosts_of(cidr: str) -> list[str]:
    """Every usable address of the network, as text, in order."""
    return [str(host) for host in check_scan_range(cidr).hosts()]


def network_of(ip: str, mask: str) -> str:
    """The CIDR of an address and its mask (255.255.255.0 -> 192.168.0.0/24), or '' when the mask is not a mask."""
    try:
        return str(ipaddress.ip_network(f"{ip}/{mask}", strict=False))
    except ValueError:
        return ""


def is_mask(text: str) -> bool:
    """A dotted-quad netmask: some ones and then zeros."""
    try:
        value = int(ipaddress.IPv4Address(text))
    except ValueError:
        return False
    inverted = value ^ 0xFFFFFFFF
    return value != 0 and (inverted & (inverted + 1)) == 0


def dashed(ip: str) -> str:
    """192.168.0.7 -> 192-168-0-7, the form of a device id that is known only by its address."""
    return ip.replace(".", "-")
