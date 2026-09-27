"""The command line of ARMOR-NETWORK.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

    armor-network scan                      # look at the network once and print what is there
    armor-network internet                  # one round of the internet check
    armor-network watch --server-url http://127.0.0.1:8080 --ingest-token ...    # keep watching and tell the server
    armor-network demo  --server-url ...    # the same with a made-up house (nothing is probed)
    armor-network oui 24:0a:c4:11:22:33     # who made a network card

It only reads: see the notes at the top of system_io.py for everything it sends.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from . import __version__, oui
from .agent import Agent, Config
from .ipnet import ScanRefused, check_scan_range
from .publisher import DeliveryError, check_server_url, post
from .services import PROFILES
from .sim_io import SimIO
from .system_io import SystemIO


def _validator():
    """ARMOR-COMMON's validator when it is next to this project (or installed); None otherwise."""
    for candidate in (Path(__file__).resolve().parents[3] / "ARMOR-COMMON" / "src",):
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    try:
        from armor_common import validate_network_message
    except ImportError:
        return None
    return validate_network_message


def _common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--node-id", default="network-1", help="the name of this node in the messages (lowercase letters, digits, - and _)")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="quick", help="how many ports to look at on each device")
    parser.add_argument("--no-ports", action="store_true", help="do not look at ports at all")
    parser.add_argument("--skip", action="append", default=[], metavar="IP", help="an address never to probe (something fragile); repeatable")
    parser.add_argument("--cidr", help="the network to scan, when it is not the one of the interface with the default route; always a private range of at most 1024 addresses")


def _print_summary(message: dict) -> None:
    internet = message["internet"]
    interface = message["interface"]
    print(f"Interface {interface['name']}  {interface['ip']}  network {interface['cidr']}  router {interface.get('gateway', '-')}")
    latency = f"  {internet['latency_ms']} ms" if "latency_ms" in internet else ""
    print(f"Internet: {internet['state']}{latency}   outages in 24 h: {internet.get('outages_24h', 0)}  without internet: {internet.get('downtime_24h_s', 0)} s")
    for probe in internet.get("probes", []):
        print(f"   {'ok ' if probe['ok'] else 'FAIL'}  {probe['kind']:<4} {probe['target']}" + (f"  {probe['latency_ms']} ms" if "latency_ms" in probe else ""))
    print(f"Devices: {len(message['devices'])}")
    print(f"  {'address':<15} {'MAC':<17} {'kind':<9} {'name':<22} {'maker':<28} ports")
    for device in message["devices"]:
        ports = ",".join(str(p["port"]) for p in device.get("ports", []))
        state = "" if device["online"] else "  (offline)"
        print(f"  {device['ip']:<15} {device.get('mac', '-'):<17} {device.get('kind', '?'):<9} {device.get('hostname', '-')[:22]:<22} {device.get('vendor', '-')[:28]:<28} {ports}{state}")
    for event in message["events"][-10:]:
        print(f"  event {event['id']:>4} {event['kind']:<15} {event.get('detail', '')}")


def _run_loop(agent: Agent, args: argparse.Namespace, *, forever: bool) -> int:
    server = check_server_url(args.server_url) if args.server_url else None
    token = args.ingest_token or os.environ.get("ARMOR_INGEST_TOKEN", "")
    if bool(server) != bool(token):
        print("--server-url and --ingest-token (or ARMOR_INGEST_TOKEN) must be supplied together", file=sys.stderr)
        return 2
    validate = _validator() if getattr(args, "validate", False) else None
    if getattr(args, "validate", False) and validate is None:
        print("--validate needs ARMOR-COMMON next to this project", file=sys.stderr)
        return 2
    published = 0
    try:
        while True:
            message = agent.step()
            if message is not None:
                if validate is not None:
                    validate(f"armor/network/{message['node_id']}/state", message)
                if server:
                    try:
                        post(server, token, message)
                    except DeliveryError as error:
                        print(f"ARMOR_NETWORK=UNDELIVERED {error}", file=sys.stderr)
                else:
                    print(json.dumps(message, separators=(",", ":")))
                published += 1
                if args.count and published >= args.count:
                    return 0
            if not forever and message is not None:
                return 0
            time.sleep(1.0)
    except KeyboardInterrupt:
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="armor-network", description="Look at the local network: the devices on it, whether the internet is there, what changes.")
    parser.add_argument("--version", action="version", version=f"armor-network {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="look at the network once and print it")
    _common_arguments(scan)
    scan.add_argument("--json", action="store_true", help="print the message instead of a table")

    internet = sub.add_parser("internet", help="one round of the internet check")
    internet.add_argument("--cidr")

    for name, text in (("watch", "keep watching and tell the server"), ("demo", "the same with a made-up house: nothing on the network is probed")):
        watch = sub.add_parser(name, help=text)
        _common_arguments(watch)
        watch.add_argument("--server-url", help="an ARMOR-SERVER, for example http://127.0.0.1:8080; without it the messages are printed")
        watch.add_argument("--ingest-token", help="the server's ingest token; never write it to a file (ARMOR_INGEST_TOKEN also works)")
        watch.add_argument("--data-dir", type=Path, default=Path("armor-network-data"), help="where the inventory and the outages are kept between runs")
        watch.add_argument("--scan-every", type=int, default=60, help="seconds between sweeps of the network")
        watch.add_argument("--internet-every", type=int, default=5, help="seconds between internet checks")
        watch.add_argument("--count", type=int, default=0, help="stop after this many messages (0: never)")
        watch.add_argument("--validate", action="store_true", help="check every message against ARMOR-COMMON before it is sent")
        if name == "demo":
            watch.add_argument("--tick-s", type=int, default=10, help="seconds of the made-up house's clock per real second's scripted step")

    lookup = sub.add_parser("oui", help="who made a network card")
    lookup.add_argument("mac")

    args = parser.parse_args(argv)
    if args.command == "oui":
        mac = oui.normalize_mac(args.mac)
        if mac is None:
            print("not a MAC address", file=sys.stderr)
            return 2
        print(f"{mac}  {'randomised (not a real identity)' if oui.is_randomized(mac) else (oui.vendor(mac) or 'unknown maker')}   ({oui.table_size()} makers in the table)")
        return 0
    try:
        if getattr(args, "cidr", None):
            check_scan_range(args.cidr)
        if args.command == "internet":
            io = SystemIO(cidr=args.cidr)
            agent = Agent(io, Config())
            for _ in range(3):
                agent.monitor.feed(io.now_ms(), io.probe_gateway(io.interface()["gateway"]) if io.interface().get("gateway") else None, io.probe_internet())
                time.sleep(1.0)
            status = agent.monitor.status(io.now_ms())
            print(json.dumps(status, indent=1))
            return 0 if status["state"] in ("up", "degraded") else 1
        skip = {s for s in args.skip}
        for address in skip:
            if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", address):
                print(f"--skip {address!r} is not an address", file=sys.stderr)
                return 2
        if args.command == "scan":
            agent = Agent(SystemIO(cidr=args.cidr), Config(node_id=args.node_id, profile=args.profile, no_ports=args.no_ports, skip=skip))
            message = None
            while message is None:
                message = agent.step()
            print(json.dumps(message, indent=1) if args.json else "", end="\n" if args.json else "")
            if not args.json:
                _print_summary(message)
            return 0
        config = Config(node_id=args.node_id, profile=args.profile, no_ports=args.no_ports, skip=skip, data_dir=args.data_dir, scan_every_s=args.scan_every,
                        internet_every_s=args.internet_every)
        if args.command == "demo":
            io = SimIO(tick_ms=args.tick_s * 1000)
            config.scan_every_s, config.internet_every_s, config.publish_every_s = args.tick_s, max(2, args.tick_s // 2), max(2, args.tick_s // 2)
            config.offline_after_s = args.tick_s * 3
        else:
            io = SystemIO(cidr=args.cidr)
        return _run_loop(Agent(io, config), args, forever=True)
    except ScanRefused as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"ARMOR_NETWORK=ERROR {error}", file=sys.stderr)
        return 1
