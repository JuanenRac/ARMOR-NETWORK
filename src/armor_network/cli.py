"""The command line of ARMOR-NETWORK.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

    armor-network scan                      # look at the network once and print what is there
    armor-network internet                  # one round of the internet check
    armor-network watch --server-url http://127.0.0.1:18080 --ingest-token ...    # keep watching and tell the server
    armor-network demo  --server-url ...    # the same with a made-up house (nothing is probed)
    armor-network oui 24:0a:c4:11:22:33     # who made a network card

It only reads: see the notes at the top of system_io.py for everything it sends.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
import time
from pathlib import Path

from . import __version__, config_file, oui, router_login
from .agent import Agent, Config, NetworkIO
from .ipnet import ScanRefused, check_scan_range, is_private_address
from .mqtt_out import NODE_ID, MqttError, check_mqtt_url, publish as mqtt_publish
from .orders import DEFAULT_PUBLIC_URL, check_dns_name, check_public_url
from .publisher import DeliveryError, check_server_url, deliver
from .seal import seal_text
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


def _is_local(server: str) -> bool:
    from urllib.parse import urlparse
    host = (urlparse(server).hostname or "").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback   # an address, not a name that merely starts with "127." (127.evil.example is somebody else's machine)
    except ValueError:
        return False


def _run_loop(agent: Agent, args: argparse.Namespace, *, forever: bool) -> int:
    try:
        server = check_server_url(args.server_url) if args.server_url else None
    except ValueError as error:      # a login or a path in the address: said as a message, not as a traceback
        print(str(error), file=sys.stderr)
        return 2
    token = args.ingest_token or os.environ.get("ARMOR_INGEST_TOKEN", "")
    try:
        mqtt_url = check_mqtt_url(args.mqtt_url) if getattr(args, "mqtt_url", "") else ""
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    mqtt_password = os.environ.get("ARMOR_NETWORK_MQTT_PASSWORD", "")
    if mqtt_url and (not NODE_ID.fullmatch(args.node_id) or (mqtt_password and not args.mqtt_user)):
        print("--mqtt-url needs a node id of lowercase letters, digits, - and _, and a password needs --mqtt-user", file=sys.stderr)
        return 2
    if bool(server) != bool(token):
        print("--server-url and --ingest-token (or ARMOR_INGEST_TOKEN) must be supplied together", file=sys.stderr)
        return 2
    if server and server.startswith("http://") and not _is_local(server):
        # The ingest token and the results of an inspection travel with the message: over plain HTTP anyone on the path reads them. HTTPS, or a server on this same machine, is the way.
        print("warning: the server is spoken to over plain HTTP: the ingest token and what the node finds cross the network in the clear (use an https:// address)", file=sys.stderr)
    validate = _validator() if getattr(args, "validate", False) else None
    if getattr(args, "validate", False) and validate is None:
        print("--validate needs ARMOR-COMMON next to this project", file=sys.stderr)
        return 2
    published = 0
    failures = 0           # consecutive deliveries that failed: the wait before the next try grows with them, up to five minutes
    retry_at = 0.0
    try:
        while True:
            message = agent.step()
            if message is not None:
                if validate is not None:
                    validate(f"armor/network/{message['node_id']}/state", message)
                if server:
                    if time.monotonic() >= retry_at:
                        try:
                            agent.submit(deliver(server, token, message))
                            failures = 0
                        except DeliveryError as error:
                            failures += 1
                            retry_at = time.monotonic() + min(300, 10 * 2 ** min(failures, 5))
                            print(f"ARMOR_NETWORK=UNDELIVERED {error} (next try in {int(retry_at - time.monotonic())} s)", file=sys.stderr)
                elif not mqtt_url:
                    print(json.dumps(message, separators=(",", ":")))
                if mqtt_url:
                    try:
                        mqtt_publish(mqtt_url, f"armor/network/{message['node_id']}/state", json.dumps(message, separators=(",", ":")).encode(), args.mqtt_user, mqtt_password, f"armor-network-{message['node_id']}")
                    except MqttError as error:
                        print(f"ARMOR_NETWORK=MQTT_UNDELIVERED {error}", file=sys.stderr)
                published += 1
                if args.count and published >= args.count:
                    return 0
            if not forever and message is not None:
                return 0
            time.sleep(1.0)
    except KeyboardInterrupt:
        return 0


def _ask_password() -> str:
    """The password typed by someone at the keyboard (not echoed); empty when nobody is there."""
    if not sys.stdin or not sys.stdin.isatty():
        return ""
    import getpass
    return getpass.getpass("Router password: ")


def _router_from_settings(settings: config_file.FileSettings, token: str) -> tuple[router_login.RouterLogin | None, str]:
    """The login to the router from the settings, or (None, why not). The password is never stored in clear text (see router_login.py)."""
    if not settings.router_user:
        return None, "router_user is not set in the config file"
    password, _ = router_login.resolve_password(settings.router_credential, settings.router_credential_sealed, token, dict(os.environ), _ask_password)
    if not password:
        return None, router_login.missing_password_reason(settings.router_credential, settings.router_credential_sealed, token)
    return router_login.RouterLogin(settings.router_kind, settings.router_url, settings.router_user, password, settings.router_allow_plain_http), ""


def _router_seal(token: str) -> int:
    if not token:
        print("router-seal needs this node's token (--ingest-token or ARMOR_INGEST_TOKEN)", file=sys.stderr)
        return 2
    password = os.environ.get(router_login.ROUTER_LOGIN_ENV, "") or _ask_password()
    if not password:
        print(f"the password is read from {router_login.ROUTER_LOGIN_ENV} or typed at the keyboard", file=sys.stderr)
        return 2
    sys.stdout.write(seal_text(token, password) + "\n")   # the sealed text is what the file is meant to hold; the password itself is never shown
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
        watch.add_argument("--server-url", help="an ARMOR-SERVER, for example http://127.0.0.1:18080; without it the messages are printed")
        watch.add_argument("--ingest-token", help="this node's own token (Studio shows it), or the server's shared ingest token, which cannot open a saved login for `inspect`; never write it to a file (ARMOR_INGEST_TOKEN also works)")
        watch.add_argument("--data-dir", type=Path, default=Path("armor-network-data"), help="where the inventory and the outages are kept between runs")
        watch.add_argument("--scan-every", type=int, default=60, help="seconds between sweeps of the network")
        watch.add_argument("--internet-every", type=int, default=5, help="seconds between internet checks")
        watch.add_argument("--count", type=int, default=0, help="stop after this many messages (0: never)")
        watch.add_argument("--validate", action="store_true", help="check every message against ARMOR-COMMON before it is sent")
        watch.add_argument("--no-public-info", action="store_true", help="do not ask a public service for the public address (the one request this program makes that leaves the house)")
        watch.add_argument("--dns-name", default="", help="the name the house is reached by from outside (the dynamic DNS name): it is resolved each time the public address is asked for and the message says whether it points to it")
        watch.add_argument("--rogue-dhcp", action="store_true", help="look for a second DHCP server: one DHCP question on the broadcast address every ten minutes, nothing is leased (off by default; needs permission to use the DHCP client port)")
        watch.add_argument("--dhcp-interface", metavar="IP", default="", help="the address of this machine, on the interface to look from, that the DHCP question is bound to (default: the address of the interface the default route leaves by); a private address only")
        watch.add_argument("--allow-dhcp", action="append", default=[], metavar="IP", help="a DHCP server that belongs on the network besides the router; repeatable")
        watch.add_argument("--config", type=Path, default=None, metavar="FILE", help="the file with the settings of the checks that are off by default (default: config.json in --data-dir, when it exists); a flag on the command line wins over the file")
        watch.add_argument("--router-igd", action="store_true", help="read the traffic counters of the router over UPnP (no login, read only; off by default)")
        watch.add_argument("--router-login", action="store_true", help="ask the router, WITH a login, the names of its devices (TR-064 or OpenWrt; read only; off by default; the settings and how the password is kept are in the config file, see router_login.py)")
        watch.add_argument("--mqtt-url", default="", help="also publish every message to this MQTT broker (mqtt:// or mqtts://, on armor/network/<node>/state); the manual orders do not travel this way. The password is read from ARMOR_NETWORK_MQTT_PASSWORD")
        watch.add_argument("--mqtt-user", default="", help="the user name for --mqtt-url (the account of a network node, e.g. network-node-network-1)")
        watch.add_argument("--public-info-url", default=DEFAULT_PUBLIC_URL, help="the https service that tells the public address (default: ipinfo.io)")
        if name == "demo":
            watch.add_argument("--tick-s", type=int, default=10, help="seconds of the made-up house's clock per real second's scripted step")

    lookup = sub.add_parser("oui", help="who made a network card")
    lookup.add_argument("mac")

    sealer = sub.add_parser("router-seal", help="seal the password of the router with this node's token, to put in the config file (the password is read from ARMOR_ROUTER_PASSWORD or asked for, never printed)")
    sealer.add_argument("--ingest-token", help="this node's own token (or ARMOR_INGEST_TOKEN)")

    args = parser.parse_args(argv)
    if args.command == "router-seal":
        return _router_seal(args.ingest_token or os.environ.get("ARMOR_INGEST_TOKEN", ""))
    if args.command == "oui":
        mac = oui.normalize_mac(args.mac)
        if mac is None:
            print("not a MAC address", file=sys.stderr)
            return 2
        print(f"{mac}  {'randomised (not a real identity)' if oui.is_randomized(mac) else (oui.vendor(mac) or 'unknown maker')}   ({oui.table_size()} makers in the table)")
        return 0
    if getattr(args, "node_id", None) is not None and not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", args.node_id):
        print(f"--node-id {args.node_id!r} must be lower-case letters, digits, - or _ (up to 64): the server refuses every message with any other", file=sys.stderr)
        return 2
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
        try:
            public_url = check_public_url(args.public_info_url)
            dns_name = check_dns_name(args.dns_name) if args.dns_name else ""
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
        try:
            settings = config_file.load(args.config or args.data_dir / config_file.FILE_NAME, required=args.config is not None)
        except config_file.ConfigFileError as error:
            print(f"config: {error}", file=sys.stderr)
            return 2
        dhcp_interface = args.dhcp_interface or settings.dhcp_interface   # the flags win over the file
        if dhcp_interface:
            if not is_private_address(dhcp_interface):
                print(f"--dhcp-interface {dhcp_interface!r} is not a private address", file=sys.stderr)
                return 2
        login_wanted = args.router_login or settings.router_login
        router: router_login.RouterLogin | None = None
        if login_wanted:
            router, why = _router_from_settings(settings, args.ingest_token or os.environ.get("ARMOR_INGEST_TOKEN", ""))
            if router is None:
                print(f"router login: {why}; the names are not asked of the router", file=sys.stderr)
        allowed_dhcp = set(args.allow_dhcp or settings.allow_dhcp)
        rogue_dhcp, router_igd = args.rogue_dhcp or settings.rogue_dhcp, args.router_igd or settings.router_igd
        for address in allowed_dhcp:
            try:
                ipaddress.ip_address(address)
            except ValueError:
                print(f"--allow-dhcp {address!r} is not an address", file=sys.stderr)
                return 2
        config = Config(node_id=args.node_id, profile=args.profile, no_ports=args.no_ports, skip=skip, data_dir=args.data_dir, scan_every_s=args.scan_every,
                        rogue_dhcp=rogue_dhcp, dhcp_allowed=allowed_dhcp, router_igd=router_igd, router_login=router is not None,
                        internet_every_s=args.internet_every, public_info=not args.no_public_info, public_url=public_url, dns_name=dns_name)
        loop_io: NetworkIO
        if args.command == "demo":
            loop_io = SimIO(tick_ms=args.tick_s * 1000)
            config.scan_every_s, config.internet_every_s, config.publish_every_s = args.tick_s, max(2, args.tick_s // 2), max(2, args.tick_s // 2)
            config.offline_after_s = args.tick_s * 3
        else:
            loop_io = SystemIO(cidr=args.cidr, dhcp_local=dhcp_interface or None) if router is None else SystemIO(cidr=args.cidr, dhcp_local=dhcp_interface or None, router=router)
        return _run_loop(Agent(loop_io, config), args, forever=True)
    except ScanRefused as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"ARMOR_NETWORK=ERROR {error}", file=sys.stderr)
        return 1
