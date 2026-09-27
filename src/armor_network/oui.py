"""Who made a network card: the manufacturer of a MAC address, and whether the address is a real one.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

The table (`data/oui.tsv.gz`) is the IEEE's public register of 24-bit blocks, refreshed by `tools/fetch_oui.py`. The manufacturer is a GUESS about the device: a router
made by one company may be sold under another name, and a phone with a randomised address has no manufacturer at all.
"""

from __future__ import annotations

import gzip
import re
from functools import lru_cache
from importlib import resources

MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")


def normalize_mac(text: str) -> str | None:
    """aa-bb-cc-dd-ee-ff, AA:BB:CC:DD:EE:FF or aabb.ccdd.eeff -> aa:bb:cc:dd:ee:ff; None when it is not a MAC."""
    digits = re.sub(r"[^0-9a-fA-F]", "", text)
    if len(digits) != 12 or re.search(r"[^0-9a-fA-F:.\-]", text):
        return None
    digits = digits.lower()
    return ":".join(digits[i:i + 2] for i in range(0, 12, 2))


def is_unicast(mac: str) -> bool:
    """Not a broadcast or multicast address (the low bit of the first byte)."""
    return not int(mac[:2], 16) & 1


def is_randomized(mac: str) -> bool:
    """A locally administered address (bit 1 of the first byte): what a phone or a laptop uses to keep from being followed, so it is not the device's identity."""
    return bool(int(mac[:2], 16) & 2)


@lru_cache(maxsize=1)
def _table() -> dict[str, str]:
    try:
        raw = resources.files("armor_network").joinpath("data", "oui.tsv.gz").read_bytes()
    except (FileNotFoundError, OSError):
        return {}
    table: dict[str, str] = {}
    for line in gzip.decompress(raw).decode("utf-8").splitlines():
        prefix, _, name = line.partition("\t")
        if len(prefix) == 6 and name:
            table[prefix] = name
    return table


def vendor(mac: str) -> str | None:
    """The manufacturer of the block of this MAC, or None (a randomised address has none, and a block that is not in the table neither)."""
    if is_randomized(mac):
        return None
    return _table().get(mac.replace(":", "")[:6])


def table_size() -> int:
    return len(_table())
