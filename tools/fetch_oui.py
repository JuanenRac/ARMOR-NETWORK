#!/usr/bin/env python3
"""Refresh the table of manufacturers from the IEEE's public register of MAC blocks.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

    python tools/fetch_oui.py                 # download the register and write src/armor_network/data/oui.tsv.gz
    python tools/fetch_oui.py --from oui.csv  # or read a copy of it you already have

Only the 24-bit blocks (MA-L) are kept: the ones the first three bytes of a MAC address name. The file is a table `prefix<TAB>name` in lowercase hex, compressed. The
program itself never downloads anything: this is run by a person, now and then.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import sys
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://standards-oui.ieee.org/oui/oui.csv"
OUT = Path(__file__).resolve().parents[1] / "src" / "armor_network" / "data" / "oui.tsv.gz"


def blocks(text: str) -> dict[str, str]:
    """The manufacturers in the register's CSV: {six hex digits: name}."""
    found: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("Registry") != "MA-L":
            continue
        prefix = (row.get("Assignment") or "").strip().lower()
        name = " ".join((row.get("Organization Name") or "").split())[:64]
        if len(prefix) == 6 and all(c in "0123456789abcdef" for c in prefix) and name:
            found[prefix] = name
    return found


def write(found: dict[str, str], out: Path = OUT) -> int:
    body = "".join(f"{prefix}\t{name}\n" for prefix, name in sorted(found.items()))
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(out, "wb", mtime=0) as handle:   # mtime 0: the same register gives the same file
        handle.write(body.encode("utf-8"))
    return len(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", type=Path, help="read this CSV instead of downloading it")
    args = parser.parse_args()
    if args.source:
        text = args.source.read_text(encoding="utf-8")
    else:
        request = Request(URL, headers={"User-Agent": "armor-network-fetch-oui"})
        with urlopen(request, timeout=60) as response:  # noqa: S310 - a fixed https address
            text = response.read().decode("utf-8")
    count = write(blocks(text))
    if count < 20000:
        print(f"only {count} blocks: the register looks incomplete, the file was written anyway", file=sys.stderr)
        return 1
    print(f"{count} manufacturers written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
