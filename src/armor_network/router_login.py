"""The names of the devices of the house, asked of the router WITH a login: TR-064 (Fritz!Box and the like) or the OpenWrt interface (ubus). OPT-IN, off by default.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

What it reads: the table of the devices the router knows (address, hardware address and name). What it never does: change anything on the router, read its own settings or send a
command; only the questions listed in ALLOWED_TR064 and ALLOWED_UBUS are ever built, and only to a private address.

The credential. Nothing here ever keeps it in clear text on disk:
  * "ask" (the default): not stored. It is read at each start from the environment variable ARMOR_ROUTER_PASSWORD or, when someone is at the keyboard, asked for; with neither the
    login stays off and the program says so.
  * "sealed": stored in the settings file sealed with this node's own token (the construction of seal.py), so it only opens where that token is; a changed or foreign seal opens nothing.
The password is never printed, logged or put in a message. Over plain http only TR-064 may be used, because its digest login does not send the password; the OpenWrt login does send it, so
it needs https, or an explicit `router_allow_plain_http` on a network the owner trusts (off by default).
Nothing here has been tried on a real router: the exchanges are written from the public descriptions of the two interfaces and tested against stand-ins.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from .ipnet import is_private_address
from .oui import normalize_mac
from .seal import open_sealed

KINDS = ("tr064", "openwrt")
STORES = ("ask", "sealed")
MAX_ENTRIES = 256
MAX_NAME = 63
ROUTER_LOGIN_ENV = "ARMOR_ROUTER_PASSWORD"
TR064_SERVICE = "urn:dslforum-org:service:Hosts:1"
TR064_PATH = "/upnp/control/hosts"
ALLOWED_TR064 = ("GetHostNumberOfEntries", "GetGenericHostEntry")
ALLOWED_UBUS = (("session", "login"), ("luci-rpc", "getDHCPLeases"))
NO_SESSION = "0" * 32


@dataclass
class RouterLogin:
    """What the node needs to ask the router: where, how, as whom and with which password (kept in memory only)."""
    kind: str
    url: str
    user: str
    password: str = ""
    allow_plain_http: bool = False

    def __repr__(self) -> str:   # the password never appears in a message, a log or a traceback
        return f"RouterLogin(kind={self.kind!r}, url={self.url!r}, user={self.user!r}, password={'set' if self.password else 'unset'})"


def default_url(kind: str, gateway: str) -> str:
    return f"http://{gateway}:49000" if kind == "tr064" else f"https://{gateway}"


def check_url(url: str, kind: str, allow_plain_http: bool) -> str | None:
    """Why this address cannot be used for the login, or None when it can."""
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        return "the address must be http:// or https:// with a host and no login in it"
    if not is_private_address(parts.hostname):
        return "the router must be on the local network (a private address)"
    if kind == "openwrt" and parts.scheme == "http" and not allow_plain_http:
        return "the OpenWrt login sends the password: use https, or set router_allow_plain_http on a network you trust"
    return None


def resolve_password(store: str, sealed: str, token: str, environ: dict[str, str], prompt: Callable[[], str] | None) -> tuple[str | None, str]:
    """(the password, "") or (None, why not). Nothing is written anywhere."""
    if store == "sealed":
        if not sealed or not token:
            return None, missing_password_reason(store, sealed, token)
        opened = open_sealed(token, sealed)
        return (opened, "") if opened else (None, missing_password_reason(store, sealed, token))
    value = environ.get(ROUTER_LOGIN_ENV, "")
    if value:
        return value, ""
    if prompt is not None:
        value = prompt()
        if value:
            return value, ""
    return None, missing_password_reason(store, sealed, token)


def missing_password_reason(store: str, sealed: str, token: str) -> str:
    """Why no password could be had, from the settings alone: it never sees the password, so the text is safe to show."""
    if store == "sealed":
        if not sealed:
            return "router_credential is sealed but router_credential_sealed is empty"
        if not token:
            return "a sealed router password opens only with this node's token (--ingest-token or ARMOR_INGEST_TOKEN)"
        return "the sealed router password does not open with this node's token"
    return f"the router password is not stored: set {ROUTER_LOGIN_ENV} or start the program where it can ask for it"


# ---- TR-064 -------------------------------------------------------------------------------------------------------------------------------

def tr064_request(action: str, index: int | None = None) -> tuple[bytes, dict[str, str]]:
    if action not in ALLOWED_TR064:
        raise ValueError(f"{action!r} is not one of the read-only questions")
    argument = f"<NewIndex>{int(index)}</NewIndex>" if index is not None else ""
    body = (f'<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{action} xmlns:u="{TR064_SERVICE}">{argument}</u:{action}></s:Body></s:Envelope>').encode("ascii")
    return body, {"Content-Type": 'text/xml; charset="utf-8"', "SOAPAction": f'"{TR064_SERVICE}#{action}"'}


def _tag(text: str, name: str) -> str | None:
    match = re.search(rf"<{name}>([^<]{{0,200}})</{name}>", text)
    return match.group(1).strip() if match else None


def clean_name(name: object) -> str | None:
    """A device name as it may travel: printable, no markup, short; None when nothing is left."""
    if not isinstance(name, str):
        return None
    text = "".join(ch for ch in name if ch.isprintable() and ch not in "<>&\"'")[:MAX_NAME].strip()
    return text or None


def _entry(ip: object, mac: object, name: object) -> dict[str, str] | None:
    if not isinstance(ip, str) or not is_private_address(ip):
        return None
    out = {"ip": ip}
    clean = clean_name(name)
    if clean:
        out["name"] = clean
    if isinstance(mac, str) and normalize_mac(mac):
        out["mac"] = normalize_mac(mac) or ""
    return out if "name" in out else None


def read_tr064(base_url: str, user: str, password: str, http: Callable[..., tuple[int, str]]) -> list[dict[str, str]] | None:
    """The devices the router lists. `http(url, body, headers, user, password)` returns (status, text); None when the router does not answer or refuses."""
    url = base_url.rstrip("/") + TR064_PATH
    body, headers = tr064_request("GetHostNumberOfEntries")
    status, text = http(url, body, headers, user, password)
    count = _tag(text, "NewHostNumberOfEntries") if status == 200 else None
    if count is None or not count.isdigit():
        return None
    out: list[dict[str, str]] = []
    for index in range(min(int(count), MAX_ENTRIES)):
        body, headers = tr064_request("GetGenericHostEntry", index)
        status, text = http(url, body, headers, user, password)
        if status != 200:
            continue
        entry = _entry(_tag(text, "NewIPAddress"), _tag(text, "NewMACAddress"), _tag(text, "NewHostName"))
        if entry:
            out.append(entry)
    return out


# ---- OpenWrt (ubus over HTTP) --------------------------------------------------------------------------------------------------------------

def ubus_request(session: str, obj: str, method: str, params: dict | None = None, request_id: int = 1) -> bytes:
    if (obj, method) not in ALLOWED_UBUS:
        raise ValueError(f"{obj}.{method} is not one of the read-only calls")
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "method": "call", "params": [session, obj, method, params or {}]}).encode("ascii")


def _ubus_result(text: str) -> dict | None:
    try:
        document = json.loads(text)
    except ValueError:
        return None
    result = document.get("result") if isinstance(document, dict) else None
    if isinstance(result, list) and len(result) == 2 and result[0] == 0 and isinstance(result[1], dict):
        return result[1]
    return None


def read_openwrt(base_url: str, user: str, password: str, http: Callable[..., tuple[int, str]]) -> list[dict[str, str]] | None:
    """The DHCP leases of the router. `http(url, body, headers, user, password)` returns (status, text)."""
    url = base_url.rstrip("/") + "/ubus"
    headers = {"Content-Type": "application/json"}
    status, text = http(url, ubus_request(NO_SESSION, "session", "login", {"username": user, "password": password}), headers, None, None)
    login = _ubus_result(text) if status == 200 else None
    session = login.get("ubus_rpc_session") if login else None
    if not isinstance(session, str) or not re.fullmatch(r"[0-9a-f]{32}", session):
        return None
    status, text = http(url, ubus_request(session, "luci-rpc", "getDHCPLeases", request_id=2), headers, None, None)
    leases = _ubus_result(text) if status == 200 else None
    items = leases.get("dhcp_leases") if leases else None
    if not isinstance(items, list):
        return None
    out: list[dict[str, str]] = []
    for item in items[:MAX_ENTRIES]:
        if isinstance(item, dict):
            entry = _entry(item.get("ipaddr"), item.get("macaddr"), item.get("hostname"))
            if entry:
                out.append(entry)
    return out


def read_names(login: RouterLogin, http: Callable[..., tuple[int, str]]) -> dict[str, str] | None:
    """{address: name} of the devices the router knows, or None when it could not be read. Refuses an address that is not allowed before anything is sent."""
    if check_url(login.url, login.kind, login.allow_plain_http) is not None or not login.password:
        return None
    rows = read_tr064(login.url, login.user, login.password, http) if login.kind == "tr064" else read_openwrt(login.url, login.user, login.password, http)
    if rows is None:
        return None
    return {row["ip"]: row["name"] for row in rows}
