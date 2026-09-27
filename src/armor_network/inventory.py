"""What is on the network: the devices found, what is known about each, and the events that changes make.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

The scans give observations (an address, maybe a MAC, a latency, maybe the open ports); `Inventory.observe` folds them into the devices it already knows and returns the events
that came of it: a device that appeared (`new_device`), went quiet (`device_offline`) or came back (`device_online`), changed its address (`ip_changed`), an address whose MAC
changed while the old one is still around (`arp_conflict`: two machines claiming one address, or an impostor), a port that opened or closed. The first full scan of a new
inventory only learns (the "baseline"): every device on the network that day is simply known, so the first run does not report a hundred new devices.

A device's identity is its MAC when it has one (in lowercase with colons) and `ip-<address>` when it does not, until the MAC is learned. A device with a randomised MAC
(what phones use) is identified by that address like any other, and marked so: it is not a stable identity, and a new address of the same phone is a new device.
Everything is kept in a JSON file (written atomically) so that a restart does not forget the network.
"""

from __future__ import annotations

import ipaddress
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import oui
from .ipnet import dashed
from .services import guess_kind, guess_os, service_name

MAX_EVENTS = 64
MAX_PORTS = 64
MAX_SERVICES = 16


@dataclass
class Observation:
    """One address seen by a scan. `ports` is None when the ports were not looked at this time (which is not the same as none open)."""
    ip: str
    mac: str | None = None
    latency_ms: float | None = None
    ttl: int | None = None
    hostname: str | None = None
    services: list[str] = field(default_factory=list)
    ports: dict[int, tuple[str | None, str | None]] | None = None   # port -> (service, banner)


@dataclass
class Device:
    id: str
    ip: str
    mac: str | None
    randomized: bool
    vendor: str | None
    hostname: str | None
    kind: str
    os: str | None
    online: bool
    first_seen_ms: int
    last_seen_ms: int
    latency_ms: float | None = None
    ports: dict[int, tuple[str | None, str | None]] = field(default_factory=dict)
    ports_known: bool = False          # the ports have been looked at at least once: from then on a change is an event
    services: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        """The device as the message has it (ARMOR-COMMON's network schema)."""
        out: dict = {"id": self.id, "ip": self.ip, "online": self.online, "first_seen_ms": self.first_seen_ms, "last_seen_ms": self.last_seen_ms, "kind": self.kind}
        if self.mac:
            out["mac"] = self.mac
            if self.randomized:
                out["randomized_mac"] = True
        if self.vendor:
            out["vendor"] = self.vendor
        if self.hostname:
            out["hostname"] = self.hostname
        if self.os:
            out["os"] = self.os
        if self.latency_ms is not None:
            out["latency_ms"] = round(self.latency_ms, 1)
        ports = []
        for port in sorted(self.ports)[:MAX_PORTS]:
            service, banner = self.ports[port]
            entry: dict = {"port": port, "proto": "tcp"}
            if service:
                entry["service"] = service[:32]
            if banner:
                entry["banner"] = banner[:80]
            ports.append(entry)
        if ports:
            out["ports"] = ports
        if self.services:
            out["services"] = [item[:48] for item in self.services[:MAX_SERVICES]]
        return out

    def to_record(self) -> dict:
        return {**self.to_json(), "ports_known": self.ports_known, "ports": {str(p): list(v) for p, v in self.ports.items()}, "randomized": self.randomized,
                "services": list(self.services)}

    @staticmethod
    def from_record(record: dict) -> "Device":
        return Device(id=record["id"], ip=record["ip"], mac=record.get("mac"), randomized=bool(record.get("randomized")), vendor=record.get("vendor"), hostname=record.get("hostname"),
                      kind=record.get("kind", "unknown"), os=record.get("os"), online=bool(record.get("online")), first_seen_ms=int(record["first_seen_ms"]),
                      last_seen_ms=int(record["last_seen_ms"]), latency_ms=record.get("latency_ms"),
                      ports={int(p): (v[0], v[1]) for p, v in record.get("ports", {}).items()}, ports_known=bool(record.get("ports_known")), services=list(record.get("services", [])))


class EventLog:
    """The latest events with ids that never repeat, kept across restarts. Oldest first; only the last `MAX_EVENTS` are kept."""

    def __init__(self, counter: int = 0, events: list[dict] | None = None) -> None:
        self.counter = counter
        self.events: list[dict] = list(events or [])

    def add(self, kind: str, at_ms: int, *, device_id: str | None = None, port: int | None = None, outage_s: int | None = None, detail: str | None = None) -> dict:
        self.counter += 1
        event: dict = {"id": f"e{self.counter:x}", "kind": kind, "at_ms": at_ms}
        if device_id:
            event["device_id"] = device_id
        if port is not None:
            event["port"] = port
        if outage_s is not None:
            event["outage_s"] = outage_s
        if detail:
            event["detail"] = detail[:120]
        self.events.append(event)
        del self.events[:-MAX_EVENTS]
        return event


def _ip_key(ip: str) -> int:
    return int(ipaddress.ip_address(ip))


class Inventory:
    def __init__(self, path: Path | None = None, *, offline_after_s: int = 180, conflict_window_s: int = 600, log: EventLog | None = None) -> None:
        self.path = path
        self.offline_after_ms = offline_after_s * 1000
        self.conflict_window_ms = conflict_window_s * 1000
        self.devices: dict[str, Device] = {}
        self.log = log or EventLog()
        self.baseline_done = False
        self._reported: dict[tuple[str, str, str], int] = {}
        if path is not None:
            self.load()

    # ---- the folding of a scan into what is known --------------------------------------------------------------------------------------
    def observe(self, now_ms: int, observations: list[Observation], gateway_ip: str | None = None, mark_offline: bool = True) -> list[dict]:
        """Fold one round of observations in; returns the events it caused (also kept in the log). The first round of an inventory that has never seen anything is the baseline.
        With `mark_offline` false nobody is called offline this round: when the router itself does not answer, a device that is not seen is not a device that is gone."""
        learning = not self.baseline_done
        events: list[dict] = []
        by_ip = {device.ip: device for device in self.devices.values()}
        seen: set[str] = set()
        for obs in observations:
            device = self._find(obs, by_ip)
            mac = obs.mac
            if device is None:
                device = self._create(obs, now_ms, gateway_ip)
                if not learning:
                    note = "randomised address" if device.randomized else (device.vendor or "unknown maker")
                    events.append(self.log.add("new_device", now_ms, device_id=device.id, detail=f"{obs.ip} ({note})"))
                by_ip[device.ip] = device
            else:
                if mac and device.id.startswith("ip-"):
                    device = self._adopt_mac(device, mac)
                if device.ip != obs.ip:
                    events.append(self.log.add("ip_changed", now_ms, device_id=device.id, detail=f"{device.ip} to {obs.ip}"))
                    by_ip.pop(device.ip, None)
                    device.ip = obs.ip
                    by_ip[obs.ip] = device
            events += self._conflict(obs, device, now_ms, gateway_ip)
            if not device.online:
                device.online = True
                if not learning:
                    events.append(self.log.add("device_online", now_ms, device_id=device.id, detail=f"{device.ip} is back"))
            device.last_seen_ms = now_ms
            if obs.latency_ms is not None:
                device.latency_ms = obs.latency_ms
            if obs.hostname:
                device.hostname = obs.hostname[:64]
            for service in obs.services:
                if service and service not in device.services and len(device.services) < MAX_SERVICES:
                    device.services.append(service)
            if obs.ports is not None:
                events += self._ports(device, obs.ports, now_ms, learning)
            device.os = guess_os(obs.ttl) or device.os
            device.kind = guess_kind(is_gateway=device.ip == gateway_ip, ports=set(device.ports), services=device.services, vendor=device.vendor, hostname=device.hostname,
                                     randomized=device.randomized)
            seen.add(device.id)
        for device in self.devices.values():
            if mark_offline and device.online and device.id not in seen and now_ms - device.last_seen_ms > self.offline_after_ms:
                device.online = False
                if not learning:
                    events.append(self.log.add("device_offline", now_ms, device_id=device.id, detail=f"{device.ip} stopped answering"))
        if learning and observations:
            self.baseline_done = True
        return events

    def _find(self, obs: Observation, by_ip: dict[str, Device]) -> Device | None:
        if obs.mac:
            device = self.devices.get(obs.mac)
            if device is not None:
                return device
            unknown_mac = self.devices.get(f"ip-{dashed(obs.ip)}")
            if unknown_mac is not None:
                return unknown_mac
            return None
        existing = by_ip.get(obs.ip)
        if existing is not None:
            return existing
        return self.devices.get(f"ip-{dashed(obs.ip)}")

    def _create(self, obs: Observation, now_ms: int, gateway_ip: str | None) -> Device:
        mac = obs.mac
        ident = mac or f"ip-{dashed(obs.ip)}"
        randomized = bool(mac) and oui.is_randomized(mac)
        vendor = oui.vendor(mac) if mac else None
        device = Device(id=ident, ip=obs.ip, mac=mac, randomized=randomized, vendor=vendor, hostname=None, kind="unknown", os=None, online=True, first_seen_ms=now_ms,
                        last_seen_ms=now_ms)
        self.devices[ident] = device
        return device

    def _adopt_mac(self, device: Device, mac: str) -> Device:
        """A device that was known only by its address has told its MAC: it becomes that MAC (its history is kept)."""
        del self.devices[device.id]
        existing = self.devices.get(mac)
        if existing is not None:      # the MAC was already known under another address: the older record wins, the address one is dropped
            existing.first_seen_ms = min(existing.first_seen_ms, device.first_seen_ms)
            return existing
        device.id, device.mac = mac, mac
        device.randomized = oui.is_randomized(mac)
        device.vendor = oui.vendor(mac)
        self.devices[mac] = device
        return device

    def _conflict(self, obs: Observation, device: Device, now_ms: int, gateway_ip: str | None) -> list[dict]:
        """An address that a device other than its last owner answers for, while the last owner is still on the network."""
        if not obs.mac:
            return []
        events: list[dict] = []
        for other in self.devices.values():
            if other is device or other.ip != obs.ip or not other.mac or other.mac == obs.mac:
                continue
            still_here = other.online and now_ms - other.last_seen_ms <= self.conflict_window_ms
            key = (obs.ip, obs.mac, other.mac)
            if (still_here or obs.ip == gateway_ip) and now_ms - self._reported.get(key, -10**15) > 3_600_000:   # once an hour for the same pair, not every scan
                self._reported[key] = now_ms
                role = "the router" if obs.ip == gateway_ip else obs.ip
                events.append(self.log.add("arp_conflict", now_ms, device_id=device.id, detail=f"{role} is now answered by {obs.mac}; before by {other.mac}"))
        return events

    def _ports(self, device: Device, ports: dict[int, tuple[str | None, str | None]], now_ms: int, learning: bool) -> list[dict]:
        events: list[dict] = []
        if device.ports_known and not learning:
            for port in sorted(set(ports) - set(device.ports)):
                service = ports[port][0] or service_name(port) or ""
                events.append(self.log.add("port_opened", now_ms, device_id=device.id, port=port, detail=f"{device.ip} opened {port}/tcp {service}".strip()))
            for port in sorted(set(device.ports) - set(ports)):
                events.append(self.log.add("port_closed", now_ms, device_id=device.id, port=port, detail=f"{device.ip} closed {port}/tcp"))
        device.ports = dict(ports)
        device.ports_known = True
        return events

    # ---- the picture ------------------------------------------------------------------------------------------------------------------------
    def snapshot(self) -> list[dict]:
        """Every device as the message has it, by address."""
        return [device.to_json() for device in sorted(self.devices.values(), key=lambda d: _ip_key(d.ip))][:512]

    def find_by_ip(self, ip: str) -> Device | None:
        return next((d for d in self.devices.values() if d.ip == ip), None)

    # ---- persistence ------------------------------------------------------------------------------------------------------------------------
    def load(self) -> None:
        if self.path is None or not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.devices = {d["id"]: Device.from_record(d) for d in data.get("devices", [])}
            self.baseline_done = bool(data.get("baseline_done"))
            self.log.counter = int(data.get("counter", 0))            # the log may be shared with the internet monitor: it is filled in place
            self.log.events[:] = list(data.get("events", []))
        except (OSError, ValueError, KeyError, TypeError):
            self.devices, self.baseline_done = {}, False    # an unreadable file is a network not learned yet, not a crash

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {"version": 1, "baseline_done": self.baseline_done, "counter": self.log.counter, "events": self.log.events,
                "devices": [d.to_record() for d in self.devices.values()]}
        temporary = self.path.with_name(self.path.name + f".{os.getpid()}.tmp")
        temporary.write_text(json.dumps(body, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, self.path)
