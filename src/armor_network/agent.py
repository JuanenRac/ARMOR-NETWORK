"""The agent: what to look at, how often, and the message that comes of it.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

`Agent.step()` is called every second or so; it does whatever is due at that moment (the internet check every few seconds, a sweep of the network every minute, the ports of
each device every quarter of an hour, the announcements of the devices every few minutes) and returns the message to publish when there is something new or the time to
repeat has come. It knows the network only through a `NetworkIO` (the real one in `system_io.py`, a scripted one in `sim_io.py`), so all of it is tested without a network.

What it never does: probe an address that is not private, probe a device in the skip list (something fragile that must not be poked), scan ports more than a few hosts at a
time, or change anything on any device. It reads.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .internet import InternetMonitor, ProbeResult
from .inventory import EventLog, Inventory, Observation
from .orders import DEFAULT_PUBLIC_URL, OUTPUT_LIMIT, Order, PublicTracker, target_allowed
from .services import PROFILES


class NetworkIO(Protocol):
    settle_s: float

    def now_ms(self) -> int: ...
    def sleep(self, seconds: float) -> None: ...
    def interface(self) -> dict: ...
    def all_hosts(self) -> list[str]: ...
    def poke(self, ips: list[str]) -> None: ...
    def arp_table(self) -> dict[str, str]: ...
    def ping_many(self, ips: list[str]) -> dict[str, tuple[float, int | None]]: ...
    def scan_ports(self, ip: str, ports: tuple[int, ...]) -> dict[int, tuple[str | None, str | None]]: ...
    def discover(self) -> dict[str, dict]: ...
    def resolve(self, ip: str) -> str | None: ...
    def probe_gateway(self, gateway: str) -> bool: ...
    def probe_internet(self) -> list[ProbeResult]: ...
    def traffic(self) -> tuple[int, int] | None: ...
    def public_info(self, url: str) -> dict | None: ...
    def traceroute(self, ip: str) -> str: ...
    def wake(self, mac: str, broadcast: str) -> str: ...
    def http_look(self, ip: str, port: int) -> dict: ...
    def inspect_web(self, ip: str, port: int | None, user: str | None, password: str | None) -> dict: ...


@dataclass
class Config:
    node_id: str = "network-1"
    profile: str = "quick"                  # the ports to look at: quick or standard
    no_ports: bool = False
    scan_every_s: int = 60
    ports_every_s: int = 900
    discovery_every_s: int = 180
    internet_every_s: int = 5
    publish_every_s: int = 10
    offline_after_s: int = 180
    max_ports_per_step: int = 4
    max_names_per_step: int = 8
    traffic_every_s: int = 5
    public_info: bool = True               # ask a public service for the public address now and then (one https request, nothing about the house)
    public_url: str = DEFAULT_PUBLIC_URL
    public_every_s: int = 600
    skip: set[str] = field(default_factory=set)
    data_dir: Path | None = None


class Agent:
    def __init__(self, io: NetworkIO, config: Config | None = None) -> None:
        self.io = io
        self.config = config or Config()
        directory = self.config.data_dir
        self.log = EventLog()
        self.inventory = Inventory(directory / "inventory.json" if directory else None, offline_after_s=self.config.offline_after_s, log=self.log)
        self.monitor = InternetMonitor(directory / "internet.json" if directory else None, log=self.log)
        self._next = {"internet": 0, "scan": 0, "discovery": 0, "publish": 0, "traffic": 0, "public": 0}
        self._public = PublicTracker(directory / "public.json" if directory else None)
        self._orders: list[Order] = []
        self._results: list[dict] = []
        self._announced: dict[str, dict] = {}
        self._ports_at: dict[str, int] = {}
        self._names_tried: dict[str, int] = {}
        self._scan_info: dict | None = None
        self._counters: tuple[int, int, int] | None = None
        self._bps: tuple[int, int] | None = None

    # ---- one turn --------------------------------------------------------------------------------------------------------------------------
    def step(self) -> dict | None:
        """Do what is due now. The message to publish, or None when there is nothing to say yet."""
        now = self.io.now_ms()
        info = self.io.interface()
        events: list[dict] = []
        if self._orders:
            self._do_orders(now, info)
        if now >= self._next["internet"]:
            gateway = info.get("gateway")
            events += self.monitor.feed(now, self.io.probe_gateway(gateway) if gateway else None, self.io.probe_internet())
            self._next["internet"] = now + self.config.internet_every_s * 1000
        if self.config.public_info and now >= self._next["public"]:
            self._public.update(self.io.public_info(self.config.public_url), now)
            self._next["public"] = now + self.config.public_every_s * 1000
        if now >= self._next["discovery"]:
            self._announced.update(self.io.discover())
            self._next["discovery"] = now + self.config.discovery_every_s * 1000
        if now >= self._next["scan"]:
            events += self._scan(now, info)
            self._next["scan"] = now + self.config.scan_every_s * 1000
        if now >= self._next["traffic"]:
            self._traffic(now)
            self._next["traffic"] = now + self.config.traffic_every_s * 1000
        if events or now >= self._next["publish"]:
            self._next["publish"] = now + self.config.publish_every_s * 1000
            self.inventory.save()
            return self.build_message(now, info)
        return None

    # ---- the manual orders ---------------------------------------------------------------------------------------------------------------------
    def submit(self, orders: list[Order]) -> None:
        """Orders the server handed out; they are done at the next turn, and their results go out in the next messages."""
        self._orders.extend(orders[:4])

    def _do_orders(self, now: int, info: dict) -> None:
        orders, self._orders = self._orders, []
        for order in orders:
            try:
                result = self._execute(order, info)
            except Exception as error:   # noqa: BLE001 - whatever an order does wrong is an answer, not the end of the node
                result = {"ok": False, "output": f"the order failed: {error}"[:200]}
            result.update({"id": order.id, "type": order.type, "finished_ms": self.io.now_ms()})
            if order.device_id:
                result["device_id"] = order.device_id
            if "output" in result:
                result["output"] = str(result["output"])[:OUTPUT_LIMIT]
            self._results.append(result)
        self._results = self._results[-16:]
        self._next["publish"] = 0

    def _execute(self, order: Order, info: dict) -> dict:
        if order.type == "scan_now":
            self._next["scan"] = 0
            return {"ok": True, "output": "a sweep of the network was started"}
        network = ipaddress.ip_network(info["cidr"], strict=False)
        if order.type == "wake":
            if not order.mac:
                return {"ok": False, "output": "the device has no MAC address"}
            if order.ip and not target_allowed(order.ip, network, set(), info["ip"]):
                return {"ok": False, "output": "that address is not one of this network"}
            return {"ok": True, "output": self.io.wake(order.mac, str(network.broadcast_address))}
        if not target_allowed(order.ip, network, self.config.skip, info["ip"]):
            return {"ok": False, "output": "that address is not on the network this node watches (or it was told to leave it alone)"}
        assert order.ip is not None
        if order.type == "ping":
            answer = self.io.ping_many([order.ip]).get(order.ip)
            if answer is None:
                return {"ok": False, "output": f"{order.ip} did not answer"}
            return {"ok": True, "latency_ms": round(float(answer[0]), 2), "output": f"{order.ip} answered in {answer[0]:.1f} ms" + (f" (TTL {answer[1]})" if answer[1] else "")}
        if order.type == "traceroute":
            return {"ok": True, "output": self.io.traceroute(order.ip)}
        if order.type == "ports":
            found = self.io.scan_ports(order.ip, PROFILES["standard"])
            ports = [{"port": port, "proto": "tcp", **({"service": service[:32]} if service else {}), **({"banner": banner[:80]} if banner else {})}
                     for port, (service, banner) in sorted(found.items())][:64]
            return {"ok": True, "ports": ports, "output": f"{len(ports)} open port(s) of the {len(PROFILES['standard'])} looked at"}
        if order.type == "http":
            return self.io.http_look(order.ip, order.port or 80)
        if order.type == "inspect":
            return self.io.inspect_web(order.ip, order.port, order.user, order.password)
        return {"ok": False, "output": "unknown order"}

    def _scan(self, now: int, info: dict) -> list[dict]:
        started = self.io.now_ms()
        hosts = self.io.all_hosts()
        self.io.poke(hosts)
        self.io.sleep(self.io.settle_s)
        arp = self.io.arp_table()
        own_ip, gateway = info["ip"], info.get("gateway")
        skip = self.config.skip
        known_online = {d.ip for d in self.inventory.devices.values() if d.online}
        targets = sorted({*arp, *known_online, *([gateway] if gateway else [])} - {own_ip} - skip)
        pings = self.io.ping_many(targets)
        observations: list[Observation] = []
        for ip in targets:
            if ip not in arp and ip not in pings:
                continue
            latency, ttl = pings.get(ip, (None, None))
            observations.append(Observation(ip=ip, mac=arp.get(ip), latency_ms=latency, ttl=ttl))
        try:
            own_name = socket.gethostname()
        except OSError:
            own_name = None
        observations.append(Observation(ip=own_ip, mac=info.get("mac"), latency_ms=0.0, hostname=own_name))
        names_left, ports_left = self.config.max_names_per_step, self.config.max_ports_per_step
        for obs in observations:
            note = self._announced.get(obs.ip)
            if note:
                obs.hostname = obs.hostname or note.get("hostname")
                obs.services = list(note.get("services", []))
            device = self.inventory.find_by_ip(obs.ip)
            if not obs.hostname and not (device and device.hostname) and names_left > 0 and obs.ip != own_ip and now - self._names_tried.get(obs.ip, -10**15) > 3_600_000:
                names_left -= 1
                self._names_tried[obs.ip] = now
                obs.hostname = self.io.resolve(obs.ip)
            if self.config.no_ports or obs.ip in skip or ports_left <= 0:
                continue
            never = device is None or not device.ports_known
            if never or now - self._ports_at.get(obs.ip, -10**15) >= self.config.ports_every_s * 1000:
                ports_left -= 1
                self._ports_at[obs.ip] = now
                obs.ports = self.io.scan_ports(obs.ip, PROFILES.get(self.config.profile, PROFILES["quick"]))
        events = self.inventory.observe(now, observations, gateway, mark_offline=self.monitor.gateway_ok is not False)
        self._scan_info = {"last_ms": now, "hosts": min(len(hosts), 1024), "duration_ms": max(0, self.io.now_ms() - started)}
        return events

    def _traffic(self, now: int) -> None:
        counters = self.io.traffic()
        if counters is None:
            return
        if self._counters is not None:
            seconds = (now - self._counters[0]) / 1000
            if seconds >= 1 and counters[0] >= self._counters[1] and counters[1] >= self._counters[2]:
                self._bps = (int((counters[0] - self._counters[1]) * 8 / seconds), int((counters[1] - self._counters[2]) * 8 / seconds))
                self._counters = (now, counters[0], counters[1])
        else:
            self._counters = (now, counters[0], counters[1])

    # ---- the message -----------------------------------------------------------------------------------------------------------------------
    def build_message(self, now: int, info: dict | None = None) -> dict:
        """The state as ARMOR-COMMON's `network` schema has it."""
        info = info or self.io.interface()
        interface: dict = {"name": str(info["name"])[:64] or "lan", "ip": info["ip"], "cidr": info["cidr"]}
        if info.get("gateway"):
            interface["gateway"] = info["gateway"]
        if self._bps is not None:
            interface["rx_bps"], interface["tx_bps"] = self._bps
        message = {"kind": "network", "node_id": self.config.node_id, "timestamp_ms": now, "interface": interface, "internet": self.monitor.status(now),
                   "devices": self.inventory.snapshot(), "events": list(self.log.events)}
        if self._scan_info is not None:
            message["scan"] = dict(self._scan_info)
        public = self._public.block() if self.config.public_info else None
        if public is not None:
            message["public"] = public
        # A result goes out in every message for two minutes, so one that is lost on the way is not lost (the server counts a result it reads twice once).
        recent = [r for r in self._results if now - r["finished_ms"] <= 120_000]
        if recent:
            message["results"] = recent[-16:]
        return message
