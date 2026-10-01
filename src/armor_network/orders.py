"""The public side of the connection and the manual orders the server may hand the node.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Two things that are not about the house's own devices:

* the public address (and who gives it), asked of a public service every few minutes - one HTTPS request to a fixed address, nothing about the
  house in it; a node can be told not to (`--no-public-info`);
* the orders an operator gives from Studio (a sweep now, a ping, a traceroute, a wake-up, a look at the ports or the web page of one device).
  They arrive in the answer to the node's own message, never as a connection made to the node, and each is checked here before anything is done:
  the type must be one of seven, the address must be private and on the network the node watches, and nothing is ever run through a shell.
"""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import ssl
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .ipnet import is_private_address

ORDER_TYPES = ("scan_now", "ping", "traceroute", "wake", "ports", "http", "inspect")
ORDER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
MAC = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
DEFAULT_PUBLIC_URL = "https://ipinfo.io/json"
MAX_ORDERS_AT_ONCE = 4
OUTPUT_LIMIT = 2000
_FIELDS = (("hostname", 128), ("city", 64), ("region", 64), ("country", 64), ("org", 128), ("timezone", 64))


def check_public_url(url: str) -> str:
    """Only an https address with a host name: what is asked of a public service travels encrypted and goes where the person said."""
    if not re.fullmatch(r"https://[A-Za-z0-9.-]+(:\d{1,5})?(/[A-Za-z0-9._~/%-]*)?", url or ""):
        raise ValueError("--public-info-url must be a plain https address such as https://ipinfo.io/json")
    return url


def fetch_public_info(url: str = DEFAULT_PUBLIC_URL, timeout: float = 6.0) -> dict | None:
    """The public address and what the service says of it (city, provider...), or None when it could not be had. Never raises."""
    try:
        request = Request(check_public_url(url), headers={"User-Agent": "armor-network", "Accept": "application/json"})
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - https, checked by check_public_url
            data = json.loads(response.read(8192).decode("utf-8", "replace"))
    except (OSError, URLError, ValueError):
        return None
    return clean_public_info(data)


def clean_public_info(data: object) -> dict | None:
    """What a service answered, reduced to what the contract holds: a real address and short plain texts."""
    if not isinstance(data, dict):
        return None
    try:
        ip = str(ipaddress.ip_address(str(data.get("ip", "")).strip()))
    except ValueError:
        return None
    out: dict = {"ip": ip}
    for key, limit in _FIELDS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()[:limit]
    return out


class PublicTracker:
    """Keeps the last public answer and when the address was seen to change, between runs when there is a folder."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.info: dict | None = None
        self.checked_ms = 0
        self.changed_ms: int | None = None
        if path is not None and path.is_file():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                self.info = clean_public_info(saved.get("info"))
                self.changed_ms = int(saved["changed_ms"]) if isinstance(saved.get("changed_ms"), int) else None
            except (OSError, ValueError, TypeError, KeyError):
                self.info = None

    def update(self, info: dict | None, now_ms: int) -> None:
        self.checked_ms = now_ms
        if info is None:
            return
        if self.info is not None and self.info.get("ip") != info["ip"]:
            self.changed_ms = now_ms
        self.info = info
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps({"info": info, "changed_ms": self.changed_ms}, separators=(",", ":")), encoding="utf-8")
            except OSError:
                pass

    def block(self) -> dict | None:
        """The `public` block of the message (None until the first answer)."""
        if self.info is None:
            return None
        out = dict(self.info)
        out["checked_ms"] = self.checked_ms
        if self.changed_ms is not None:
            out["changed_ms"] = self.changed_ms
        return out


@dataclass(frozen=True)
class Order:
    id: str
    type: str
    ip: str | None = None
    mac: str | None = None
    device_id: str | None = None
    port: int | None = None
    # the login the person gave for this one order (an `inspect`): kept out of every printout, used once and never stored
    user: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False, compare=False)


def parse_orders(body: object) -> list[Order]:
    """The orders in the server's answer: the well-formed ones only, at most four, and nothing else in the answer is looked at."""
    commands = body.get("commands") if isinstance(body, dict) else None
    if not isinstance(commands, list):
        return []
    orders: list[Order] = []
    for item in commands[:MAX_ORDERS_AT_ONCE]:
        if not isinstance(item, dict) or item.get("type") not in ORDER_TYPES:
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or not ORDER_ID.match(identifier):
            continue
        ip, mac, device_id, port = item.get("ip"), item.get("mac"), item.get("device_id"), item.get("port")
        auth = item.get("auth") if item["type"] == "inspect" and isinstance(item.get("auth"), dict) else {}
        user = auth.get("user") if isinstance(auth.get("user"), str) and 0 < len(auth["user"]) <= 64 else None
        password = auth.get("password") if isinstance(auth.get("password"), str) and len(auth["password"]) <= 128 else None
        orders.append(Order(identifier, item["type"], ip if isinstance(ip, str) else None, mac.lower() if isinstance(mac, str) and MAC.match(mac.lower()) else None,
                            device_id if isinstance(device_id, str) and len(device_id) <= 64 else None,
                            port if isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65_535 else None, user, password if user is not None else None))
    return orders


def magic_packet(mac: str) -> bytes:
    """The wake-on-LAN packet: six bytes of 0xff and the MAC sixteen times."""
    raw = bytes.fromhex(mac.replace(":", ""))
    if len(raw) != 6:
        raise ValueError("a MAC address has six bytes")
    return b"\xff" * 6 + raw * 16


def send_magic_packet(mac: str, broadcast: str) -> None:
    """Broadcast the packet on the local network (UDP port 9) - to the network's own broadcast address, never beyond it."""
    packet = magic_packet(mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2.0)
        sock.sendto(packet, (broadcast, 9))


def http_look(ip: str, port: int, timeout: float = 3.0) -> dict:
    """One GET of the front page of a device: the status, the server it says it is and the title. A device's own certificate is not checked (it is almost always its own)."""
    scheme = "https" if port in (443, 8443, 4443, 8883) else "http"
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    request = Request(f"{scheme}://{ip}:{port}/", headers={"User-Agent": "armor-network", "Accept": "text/html,*/*"})
    try:
        with urlopen(request, timeout=timeout, context=context if scheme == "https" else None) as response:  # noqa: S310 - a private address, checked before
            status, server = response.status, response.headers.get("Server", "")
            body = response.read(16_384).decode("utf-8", "replace")
    except OSError as error:
        return {"ok": False, "output": f"no answer: {error}"[:200]}
    match = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    title = re.sub(r"\s+", " ", match.group(1)).strip()[:120] if match else ""
    parts = [f"{scheme}://{ip}:{port}/ -> HTTP {status}"]
    if server:
        parts.append(f"server: {server[:80]}")
    if title:
        parts.append(f"title: {title}")
    return {"ok": True, "output": "\n".join(parts)}


def target_allowed(ip: str | None, network: ipaddress.IPv4Network, skip: set[str], own_ip: str) -> bool:
    """An order may only be about an address that is private, on the network the node watches, not its own and not one it was told to leave alone."""
    if not ip or not is_private_address(ip):
        return False
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return address in network and ip != own_ip and ip not in skip


# What a person is told to change: the pairs a factory leaves in a device. The node only ever tries the ONE pair the person gave for the order; it never goes through this list to guess.
FACTORY_LOGINS = {("admin", "admin"), ("admin", ""), ("admin", "1234"), ("admin", "12345"), ("admin", "123456"), ("admin", "password"), ("admin", "admin123"), ("root", "root"),
                  ("root", ""), ("user", "user"), ("guest", "guest"), ("administrator", "administrator"), ("admin", "9999"), ("admin", "888888")}
_HINTS = (("model", re.compile(r"(?:device\s*model|model(?:\s*name)?|product)\s*[:=\"'>]\s*([A-Za-z0-9][A-Za-z0-9 ._/-]{1,39})", re.I)),
          ("firmware", re.compile(r"(?:firmware(?:\s*version)?|fw\s*version|software\s*version)\s*[:=\"'>]\s*([A-Za-z0-9][A-Za-z0-9 ._/-]{1,39})", re.I)),
          ("serial", re.compile(r"(?:serial(?:\s*(?:no|number))?)\s*[:=\"'>]\s*([A-Za-z0-9][A-Za-z0-9._-]{3,29})", re.I)))


def _open(url: str, user: str | None, password: str | None, context: ssl.SSLContext | None, timeout: float):
    """One GET, with the login when there is one (Basic or Digest, whichever the device asks for)."""
    from urllib.request import HTTPBasicAuthHandler, HTTPDigestAuthHandler, HTTPPasswordMgrWithDefaultRealm, HTTPSHandler, build_opener
    handlers = []
    if user is not None:
        manager = HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, url, user, password or "")
        handlers += [HTTPBasicAuthHandler(manager), HTTPDigestAuthHandler(manager)]
    if context is not None:
        handlers.append(HTTPSHandler(context=context))
    opener = build_opener(*handlers)
    return opener.open(Request(url, headers={"User-Agent": "armor-network", "Accept": "text/html,*/*"}), timeout=timeout)  # noqa: S310 - a private address, checked before


def _inspect_one(ip: str, port: int, user: str | None, password: str | None, timeout: float) -> dict | None:
    scheme = "https" if port in (443, 8443, 4443) else "http"
    url = f"{scheme}://{ip}:{port}/"
    context = None
    if scheme == "https":
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE   # a device's own certificate is almost always its own
    needs, challenge, status, server, body = False, "", 0, "", ""
    try:                                      # first without the login: does it ask for one, and which kind?
        with _open(url, None, None, context, timeout) as response:
            status, server = response.status, response.headers.get("Server", "")
            body = response.read(16_384).decode("utf-8", "replace")
    except HTTPError as error:
        status, server = error.code, error.headers.get("Server", "")
        challenge = error.headers.get("WWW-Authenticate", "")
        needs = error.code == 401
        body = error.read(16_384).decode("utf-8", "replace") if error.fp else ""
    except OSError:
        return None
    login = "not required"
    if needs:
        scheme_name = challenge.split(" ")[0] if challenge else "unknown"
        realm = re.search(r'realm="([^"]{1,60})"', challenge)
        if user is None:
            login = f"required ({scheme_name}), no login was given"
        else:
            try:
                with _open(url, user, password, context, timeout) as response:
                    status, body = response.status, response.read(16_384).decode("utf-8", "replace")
                    server = response.headers.get("Server", server)
                login = f"accepted ({scheme_name})"
                if (user.lower(), password or "") in FACTORY_LOGINS:
                    login += " - it is a factory login: change it"
            except HTTPError as error:
                status = error.code
                login = "refused" if error.code == 401 else f"refused (HTTP {error.code})"
            except OSError as error:
                login = f"not tried: {error}"[:80]
        if realm:
            login += f"; realm: {realm.group(1)}"
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    parts = [f"{url} -> HTTP {status}", f"login: {login}"]
    if server:
        parts.append(f"server: {server[:80]}")
    if title:
        parts.append("title: " + re.sub(r"\s+", " ", title.group(1)).strip()[:120])
    for name, pattern in _HINTS:
        found = pattern.search(body)
        if found:
            parts.append(f"{name}: {found.group(1).strip()[:40]}")
    text = "\n".join(parts)
    if password:
        text = text.replace(password, "***")   # whatever the page says, the login is never echoed back
    return {"ok": not login.startswith(("refused", "not tried")), "output": text}


def inspect_web(ip: str, port: int | None, user: str | None, password: str | None, timeout: float = 4.0) -> dict:
    """Look at the web administration of one device with the login the person gave: does it ask for one, is it accepted, and what the page says about the device
    (its server, its title, a model, a firmware version, a serial number). One pair of credentials, tried once; nothing is changed on the device."""
    for candidate in ([port] if port else [80, 443, 8080, 8443]):
        result = _inspect_one(ip, candidate, user, password, timeout)
        if result is not None:
            return result
    return {"ok": False, "output": f"no web interface answered at {ip}" + (f":{port}" if port else " (ports 80, 443, 8080, 8443)")}
