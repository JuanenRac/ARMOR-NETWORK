"""A network that is not there: a house's LAN with a script of things happening to it, for the tests, for the demonstration and for developing the consoles.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

It implements the same `NetworkIO` as the real machine, so the whole agent runs against it. The devices have the makers' real blocks (looked up in the register, not written by
hand), and the script is the sort of thing that happens: an unknown device joins with a Telnet port open, a camera opens a port, a smart plug goes away and comes back, the
internet goes down while the router still answers, then the router goes away too, and, at the end, another machine starts answering for the router's address.
Time is `tick * tick_ms` from the clock it is given, so a test moves it by hand and the demonstration lets a real clock move it.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from . import oui
from .internet import ProbeResult


def _mac_of(maker_word: str, suffix: str) -> str:
    """A MAC in the first block of the register whose maker's name starts with `maker_word`, with the given last three bytes."""
    table = oui._table()
    for prefix in sorted(table):
        if table[prefix].lower().startswith(maker_word.lower()):
            return ":".join(prefix[i:i + 2] for i in (0, 2, 4)) + ":" + suffix
    return "02:00:00:" + suffix       # a locally administered one, when the register is missing


@dataclass
class SimDevice:
    ip: str
    mac: str
    hostname: str | None = None
    services: list[str] = field(default_factory=list)
    ports: dict[int, tuple[str | None, str | None]] = field(default_factory=dict)
    ttl: int = 64
    joins: int = 0                                  # the tick from which it is on the network
    leaves: int | None = None                       # and the tick at which it goes (it may come back: see `returns`)
    returns: int | None = None
    opens: dict[int, dict[int, tuple[str | None, str | None]]] = field(default_factory=dict)   # tick -> ports it has from then on


def default_devices() -> list[SimDevice]:
    return [
        SimDevice("192.168.0.1", "14:2e:5e:86:d9:62", "router", [], {80: ("http", "Router login"), 443: ("https", None), 53: ("dns", None)}, 64),
        SimDevice("192.168.0.12", "96:b3:ed:0b:1c:18", "juans-iphone", ["_companion-link._tcp"], {}, 64),
        SimDevice("192.168.0.30", _mac_of("Espressif", "11:22:33"), None, [], {80: ("http", "ESP32 Smart plug")}, 64, leaves=9, returns=15),
        SimDevice("192.168.0.203", _mac_of("Hangzhou Hikvision", "aa:bb:01"), "cam-garage", [], {80: ("http", "DNVRS-Webs"), 554: ("rtsp", None), 37777: ("dahua", None)}, 64,
                  opens={7: {80: ("http", "DNVRS-Webs"), 554: ("rtsp", None), 37777: ("dahua", None), 23: ("telnet", "login:")}}),
        SimDevice("192.168.0.40", _mac_of("Brother", "cc:dd:02"), "printer", ["_ipp._tcp"], {9100: ("jetdirect", None), 631: ("ipp", None)}, 64),
        SimDevice("192.168.0.50", _mac_of("Google", "ee:ff:03"), "Living room TV", ["_googlecast._tcp"], {8008: ("cast", None)}, 64),
        SimDevice("192.168.0.60", _mac_of("Synology", "12:34:04"), "diskstation", ["_smb._tcp"], {5000: ("http-alt", "DiskStation"), 445: ("smb", None)}, 64),
        SimDevice("192.168.0.180", _mac_of("Raspberry", "56:78:05"), "cm5", ["_ssh._tcp"], {22: ("ssh", "SSH-2.0-OpenSSH_9.2"), 3000: ("http-alt", "ARMOR")}, 64),
        SimDevice("192.168.0.77", "de:ad:be:ef:00:77", None, [], {23: ("telnet", "BusyBox login:"), 80: ("http", "Webcam")}, 64, joins=3),
    ]


class SimIO:
    settle_s = 0.0

    def __init__(self, clock: Callable[[], int] | None = None, tick_ms: int = 10_000, devices: list[SimDevice] | None = None, cidr: str = "192.168.0.0/24",
                 outage: tuple[int, int] = (11, 16), lan_outage: tuple[int, int] = (20, 23), conflict_at: int = 26) -> None:
        self._clock = clock or (lambda: int(time.time() * 1000))
        self._t0 = self._clock()
        self.tick_ms = tick_ms
        self.devices = devices if devices is not None else default_devices()
        self.cidr = cidr
        self.outage, self.lan_outage, self.conflict_at = outage, lan_outage, conflict_at
        self._counter = 0

    # ---- the script -------------------------------------------------------------------------------------------------------------------------
    @property
    def tick(self) -> int:
        return (self._clock() - self._t0) // self.tick_ms

    def _present(self, device: SimDevice) -> bool:
        tick = self.tick
        if tick < device.joins:
            return False
        if device.leaves is not None and tick >= device.leaves and (device.returns is None or tick < device.returns):
            return False
        return True

    def _ports(self, device: SimDevice) -> dict[int, tuple[str | None, str | None]]:
        ports = device.ports
        for at in sorted(device.opens):
            if self.tick >= at:
                ports = device.opens[at]
        return ports

    def _lan_down(self) -> bool:
        return self.lan_outage[0] <= self.tick < self.lan_outage[1]

    def _internet_down(self) -> bool:
        return self._lan_down() or self.outage[0] <= self.tick < self.outage[1]

    # ---- the NetworkIO --------------------------------------------------------------------------------------------------------------------
    def now_ms(self) -> int:
        return self._clock()

    def sleep(self, seconds: float) -> None:
        pass

    def interface(self) -> dict:
        return {"name": "Simulated LAN", "ip": "192.168.0.10", "cidr": self.cidr, "gateway": "192.168.0.1", "mac": "c0:35:32:d6:35:77"}

    def all_hosts(self) -> list[str]:
        from .ipnet import hosts_of

        return hosts_of(self.cidr)

    def poke(self, ips: list[str]) -> None:
        pass

    def arp_table(self) -> dict[str, str]:
        if self._lan_down():
            return {}
        table = {d.ip: d.mac for d in self.devices if self._present(d)}
        if self.tick >= self.conflict_at:
            table["192.168.0.1"] = "de:ad:be:ef:01:01"        # somebody else answers for the router
        return table

    def ping_many(self, ips: list[str]) -> dict[str, tuple[float, int | None]]:
        if self._lan_down():
            return {}
        found = {}
        by_ip = {d.ip: d for d in self.devices}
        for ip in ips:
            device = by_ip.get(ip)
            if device is not None and self._present(device) and device.hostname != "juans-iphone":    # a phone that does not answer echoes
                found[ip] = (1.0 + (int(ip.rsplit(".", 1)[1]) % 7), device.ttl)
        return found

    def scan_ports(self, ip: str, ports: tuple[int, ...]) -> dict[int, tuple[str | None, str | None]]:
        device = next((d for d in self.devices if d.ip == ip and self._present(d)), None)
        if device is None:
            return {}
        return {p: v for p, v in self._ports(device).items() if p in ports}

    def discover(self) -> dict[str, dict]:
        return {d.ip: {"hostname": d.hostname if d.services else None, "services": list(d.services)} for d in self.devices if self._present(d) and d.services}

    def resolve(self, ip: str) -> str | None:
        return next((d.hostname for d in self.devices if d.ip == ip), None)

    def probe_gateway(self, gateway: str) -> bool:
        return not self._lan_down()

    def probe_internet(self) -> list[ProbeResult]:
        if self._internet_down():
            return [ProbeResult("1.1.1.1:443", "tcp", False), ProbeResult("1.1.1.1", "dns", False), ProbeResult("8.8.8.8", "dns", False),
                    ProbeResult("connectivitycheck.gstatic.com", "http", False)]
        return [ProbeResult("1.1.1.1:443", "tcp", True, 11.0), ProbeResult("1.1.1.1", "dns", True, 13.0), ProbeResult("8.8.8.8", "dns", True, 14.0),
                ProbeResult("connectivitycheck.gstatic.com", "http", True, 38.0)]

    def traffic(self) -> tuple[int, int] | None:
        self._counter += 1
        return (self._counter * 150_000, self._counter * 40_000)
