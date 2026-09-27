"""The real network: what the agent asks of the machine and of the devices on the network it is plugged into.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Everything the program sends is listed here, and none of it is an attack: an ICMP echo and a TCP connection to a handful of ports of the devices of the private network it
watches, a UDP datagram to the discard port to make the system resolve their addresses, the multicast questions of mDNS and SSDP, a NetBIOS name request, and, for the internet
check, a TCP connection, two DNS questions and one web request to well-known public addresses. It never sends a password, never tries a login, never leaves the private
range for anything but that check (`check_scan_range`), and reads at most a few hundred bytes of what answers.
"""

from __future__ import annotations

import concurrent.futures
import ipaddress
import socket
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from . import dnswire, parsers
from .internet import ProbeResult
from .ipnet import check_scan_range, hosts_of, is_private_address, network_of
from .neighbors import in_network, parse_arp_windows, parse_ip_neigh, parse_proc_net_arp
from .oui import normalize_mac
from .services import clean_banner, parse_http, service_name

WINDOWS = sys.platform.startswith("win")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
HTTP_PORTS = {80, 8000, 8008, 8080, 8081, 3000, 5000, 9000, 18080, 18081}
TALKING_PORTS = {21, 22, 23, 25, 110, 143, 993, 1883}       # services that say something first


def bounded(function, timeout: float):
    """The result of `function()`, or None when it takes longer than `timeout` seconds. The system's name lookups ignore socket timeouts (one for a phone that does not answer
    took sixteen seconds), so the call is made in a thread that is left behind when it is too slow; the thread never keeps the program from ending."""
    box: list = []

    def work() -> None:
        try:
            box.append(function())
        except (OSError, UnicodeError):
            box.append(None)
    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(timeout)
    return box[0] if box else None


def run(command: list[str], timeout: float = 6.0) -> str:
    """The text a tool printed, in the system's own encoding; empty when it is not there or takes too long."""
    try:
        done = subprocess.run(command, capture_output=True, timeout=timeout, creationflags=NO_WINDOW if WINDOWS else 0)   # noqa: S603 - fixed argument lists, never a shell
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.decode("oem" if WINDOWS else "utf-8", "replace")


class SystemIO:
    """The `NetworkIO` of the real machine (see agent.py)."""

    settle_s = 1.5      # how long the system gets to learn the neighbours after they were poked

    def __init__(self, cidr: str | None = None, interface_ip: str | None = None) -> None:
        self._cidr_override = cidr
        self._interface_ip = interface_ip
        self._info: dict | None = None

    # ---- the clock and the interface ---------------------------------------------------------------------------------------------------------
    def now_ms(self) -> int:
        return int(time.time() * 1000)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def interface(self) -> dict:
        """{"name", "ip", "cidr", "gateway", "mac"}: the interface the default route leaves by. The network is the one of its address and mask unless it was given."""
        if self._info is not None:
            return self._info
        gateway = ip = None
        name = "lan"
        mac = None
        mask_cidr = None
        if WINDOWS:
            found = parsers.parse_route_windows(run(["route", "print", "-4"]))
            if found:
                gateway, ip = found
            for adapter in parsers.parse_ipconfig(run(["ipconfig", "/all"])):
                if ip in adapter.ips:
                    name, mac = adapter.name, adapter.mac
                    if ip in adapter.masks:
                        mask_cidr = network_of(ip, adapter.masks[ip])
        else:
            route = parsers.parse_ip_route(run(["ip", "route", "show", "default"]))
            if route:
                gateway, device = route
                for iface, address in parsers.parse_ip_addr(run(["ip", "-o", "-4", "addr", "show"])):
                    if iface == device:
                        ip, name = address.split("/")[0], iface
                        mask_cidr = str(ipaddress.ip_interface(address).network)
                        try:
                            mac = normalize_mac(open(f"/sys/class/net/{iface}/address", encoding="ascii").read().strip())
                        except OSError:
                            mac = None
        if self._interface_ip:
            ip = self._interface_ip
        if not ip:
            raise RuntimeError("no default route: this machine is not on a network")
        cidr = self._cidr_override or mask_cidr or network_of(ip, "255.255.255.0")
        check_scan_range(cidr)
        self._info = {"name": name, "ip": ip, "cidr": cidr, "gateway": gateway, "mac": mac}
        return self._info

    # ---- who is there ----------------------------------------------------------------------------------------------------------------------------
    def poke(self, ips: list[str]) -> None:
        """A one-byte datagram to the discard port of every address: nobody answers it, and the system asks who has each address, which is what fills its neighbour table."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setblocking(False)
            for ip in ips:
                if not is_private_address(ip):
                    continue
                try:
                    sock.sendto(b"\x00", (ip, 9))
                except (BlockingIOError, OSError):
                    pass
        finally:
            sock.close()

    def arp_table(self) -> dict[str, str]:
        cidr = self.interface()["cidr"]
        if WINDOWS:
            table = parse_arp_windows(run(["arp", "-a"]))
        else:
            try:
                with open("/proc/net/arp", encoding="ascii") as handle:
                    table = parse_proc_net_arp(handle.read())
            except OSError:
                table = parse_ip_neigh(run(["ip", "neigh"]))
        return in_network(table, cidr)

    def ping_many(self, ips: list[str], timeout_ms: int = 800, workers: int = 32) -> dict[str, tuple[float, int | None]]:
        """The devices that answered an echo: ip -> (milliseconds, TTL)."""
        def one(ip: str):
            command = ["ping", "-n", "1", "-w", str(timeout_ms), ip] if WINDOWS else ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), ip]
            return ip, parsers.parse_ping(run(command, timeout=timeout_ms / 1000 + 3))
        found = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for ip, reply in pool.map(one, [ip for ip in ips if is_private_address(ip)]):
                if reply is not None:
                    found[ip] = reply
        return found

    # ---- what each one offers ----------------------------------------------------------------------------------------------------------------
    def scan_ports(self, ip: str, ports: tuple[int, ...], timeout: float = 0.6) -> dict[int, tuple[str | None, str | None]]:
        """The open TCP ports of one device with the service each is known for and what it says. Twelve connections at a time at most, and only to a private address."""
        if not is_private_address(ip):
            return {}

        def probe(port: int):
            try:
                with socket.create_connection((ip, port), timeout=timeout) as sock:
                    return port, self._banner(sock, ip, port)
            except OSError:
                return None
        found: dict[int, tuple[str | None, str | None]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            for result in pool.map(probe, ports):
                if result is not None:
                    port, banner = result
                    found[port] = (service_name(port), banner)
        return found

    @staticmethod
    def _banner(sock: socket.socket, ip: str, port: int) -> str | None:
        sock.settimeout(0.5)
        try:
            if port in HTTP_PORTS:
                sock.sendall(f"GET / HTTP/1.0\r\nHost: {ip}\r\nUser-Agent: armor-network\r\nConnection: close\r\n\r\n".encode("ascii"))
                return parse_http(sock.recv(2048))
            if port in TALKING_PORTS:
                return clean_banner(sock.recv(256))
        except OSError:
            return None
        return None

    def discover(self, listen_s: float = 2.5) -> dict[str, dict]:
        """What devices announce about themselves: {ip: {"hostname", "services"}} from mDNS and SSDP (the multicast questions, and what comes back)."""
        found: dict[str, dict] = {}

        def entry(ip: str) -> dict:
            return found.setdefault(ip, {"hostname": None, "services": []})
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.settimeout(0.3)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            try:
                sock.sendto(dnswire.build_query("_services._dns-sd._udp.local", dnswire.TYPE_PTR, query_id=0, recursion=False), ("224.0.0.251", 5353))
                search = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\nST: ssdp:all\r\n\r\n").encode("ascii")
                sock.sendto(search, ("239.255.255.250", 1900))
            except OSError:
                return found
            locations: dict[str, str] = {}
            end = time.monotonic() + listen_s
            while time.monotonic() < end:
                try:
                    data, (ip, port) = sock.recvfrom(4096)
                except (socket.timeout, OSError):
                    continue
                if not is_private_address(ip):
                    continue
                if port == 5353:
                    try:
                        message = dnswire.parse_message(data)
                    except ValueError:
                        continue
                    for answer in message["answers"]:
                        if answer["type"] == dnswire.TYPE_PTR and isinstance(answer["data"], str):
                            service = answer["data"].removesuffix(".local")
                            if service and service not in entry(ip)["services"]:
                                entry(ip)["services"].append(service[:48])
                        elif answer["type"] == dnswire.TYPE_A and answer["data"] == ip and answer["name"].endswith(".local"):
                            entry(ip)["hostname"] = answer["name"][:-len(".local")][:63]
                elif port == 1900:
                    headers = parsers.parse_ssdp_response(data)
                    service = parsers.ssdp_service(headers.get("ST", ""))
                    if service and service not in entry(ip)["services"]:
                        entry(ip)["services"].append(service)
                    if headers.get("LOCATION", "").startswith(f"http://{ip}:"):
                        locations.setdefault(ip, headers["LOCATION"])
        finally:
            sock.close()
        for ip, location in list(locations.items())[:20]:      # the description of a UPnP device names it (a TV says "Living room TV")
            try:
                request = Request(location, headers={"User-Agent": "armor-network"})
                with urlopen(request, timeout=1.5) as response:  # noqa: S310 - a private address, checked above
                    info = parsers.upnp_device_info(response.read(16384).decode("utf-8", "replace"))
            except (OSError, URLError, ValueError):
                continue
            if info.get("friendlyName") and not entry(ip)["hostname"]:
                entry(ip)["hostname"] = info["friendlyName"][:63]
        return found

    def resolve(self, ip: str) -> str | None:
        """A name for an address: the system's reverse DNS (the router often knows the names of what it lent an address to), then NetBIOS."""
        if not is_private_address(ip):
            return None
        found = bounded(lambda: socket.gethostbyaddr(ip)[0], 1.5)
        if found and found != ip:
            return found.split(".")[0][:63]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.settimeout(0.6)
            sock.sendto(parsers.nbstat_query(), (ip, 137))
            data, source = sock.recvfrom(1024)
            return parsers.parse_nbstat(data) if source[0] == ip else None
        except OSError:
            return None
        finally:
            sock.close()

    # ---- the router and the internet -----------------------------------------------------------------------------------------------------------
    def probe_gateway(self, gateway: str) -> bool:
        """Does the router answer: an echo, or else a TCP connection that either succeeds or is refused (a refusal comes from the router itself, so it is there)."""
        if ping := self.ping_many([gateway], timeout_ms=1000, workers=1):
            return bool(ping)
        for port in (80, 443, 53):
            try:
                socket.create_connection((gateway, port), timeout=0.8).close()
                return True
            except ConnectionRefusedError:
                return True
            except OSError:
                continue
        return False

    def probe_internet(self, timeout: float = 2.0) -> list[ProbeResult]:
        """One round of the internet check, the probes in parallel: a TCP connection to 1.1.1.1:443, a DNS question to 1.1.1.1 and another to 8.8.8.8, and the 204 page."""
        def tcp():
            start = time.perf_counter()
            try:
                socket.create_connection(("1.1.1.1", 443), timeout=timeout).close()
                return ProbeResult("1.1.1.1:443", "tcp", True, (time.perf_counter() - start) * 1000)
            except OSError:
                return ProbeResult("1.1.1.1:443", "tcp", False)

        def dns(server: str, name: str):
            start = time.perf_counter()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.settimeout(timeout)
                query = dnswire.build_query(name)
                sock.sendto(query, (server, 53))
                data, _ = sock.recvfrom(1500)
                message = dnswire.parse_message(data)
                ok = message["id"] == 0x4152 and dnswire.rcode(message) == 0 and any(a["type"] == dnswire.TYPE_A for a in message["answers"])
                return ProbeResult(server, "dns", ok, (time.perf_counter() - start) * 1000 if ok else None)
            except (OSError, ValueError):
                return ProbeResult(server, "dns", False)
            finally:
                sock.close()

        def web():
            start = time.perf_counter()
            try:
                request = Request("http://connectivitycheck.gstatic.com/generate_204", headers={"User-Agent": "armor-network"})
                with urlopen(request, timeout=timeout + 1) as response:  # noqa: S310 - a fixed address
                    ok = response.status in (200, 204)
                return ProbeResult("connectivitycheck.gstatic.com", "http", ok, (time.perf_counter() - start) * 1000 if ok else None)
            except (OSError, URLError, ValueError):
                return ProbeResult("connectivitycheck.gstatic.com", "http", False)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [pool.submit(tcp), pool.submit(dns, "1.1.1.1", "cloudflare.com"), pool.submit(dns, "8.8.8.8", "google.com"), pool.submit(web)]
            return [job.result() for job in jobs]

    # ---- how much goes through -------------------------------------------------------------------------------------------------------------------
    def traffic(self) -> tuple[int, int] | None:
        """(received, sent) bytes counted by the system: this interface's on Linux, the sum of the interfaces on Windows (`netstat -e`)."""
        if WINDOWS:
            return parsers.parse_netstat_e(run(["netstat", "-e"]))
        try:
            with open("/proc/net/dev", encoding="ascii") as handle:
                return parsers.parse_proc_net_dev(handle.read(), self.interface()["name"])
        except OSError:
            return None

    def all_hosts(self) -> list[str]:
        return hosts_of(self.interface()["cidr"])
