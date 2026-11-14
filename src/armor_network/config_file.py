"""The settings of the checks that are off by default, kept in a file (`config.json` in the data directory, or the file given with `--config`).

Every key is optional and the default of each is "off". The flags of the command line win over the file: a flag that is given is used, one that is not is read from the file.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

    {
      "rogue_dhcp": false,        look for a second DHCP server (one DHCP question on the broadcast address every ten minutes; nothing is leased)
      "allow_dhcp": [],           DHCP servers that belong on the network besides the router
      "router_igd": false,        read the traffic counters of the router over UPnP (no login, read only)
      "dhcp_interface": "",       the private address of this machine, on the interface to look from, that the DHCP question is bound to (empty: the interface the default route leaves by)
      "router_login": false,      read the names of the devices from the router WITH a login (see router_login.py); the password is never written here in clear text
      "router_kind": "tr064",     "tr064" (Fritz!Box and the like) or "openwrt"
      "router_user": "",          the user of the router
      "router_url": "",           the base address of the router (default: the gateway; http://<gateway>:49000 for tr064, https://<gateway> for openwrt); always a private address
      "router_allow_plain_http": false,   let the OpenWrt login (which sends the password) go over plain http, on a network you trust
      "router_credential": "ask", "ask" (not stored: read from ARMOR_ROUTER_PASSWORD or asked at each start) or "sealed" (stored below, sealed with this node's token)
      "router_credential_sealed": ""   the sealed password, made with `armor-network router-seal`
    }
"""
from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import router_login
from .ipnet import is_private_address

FILE_NAME = "config.json"
MAX_BYTES = 16_384
MAX_ALLOWED = 32


class ConfigFileError(ValueError):
    """The file cannot be used; the message says which key and why."""


@dataclass
class FileSettings:
    rogue_dhcp: bool = False
    allow_dhcp: list[str] = field(default_factory=list)
    router_igd: bool = False
    dhcp_interface: str = ""
    router_login: bool = False
    router_kind: str = "tr064"
    router_user: str = ""
    router_url: str = ""
    router_allow_plain_http: bool = False
    router_credential: str = "ask"
    router_credential_sealed: str = ""


def parse(text: str) -> FileSettings:
    try:
        document = json.loads(text)
    except ValueError as error:
        raise ConfigFileError(f"not valid JSON ({error})") from None
    if not isinstance(document, dict):
        raise ConfigFileError("the file must hold one JSON object")
    unknown = sorted(set(document) - {"rogue_dhcp", "allow_dhcp", "router_igd", "dhcp_interface", "router_login", "router_kind", "router_user", "router_url",
                                      "router_allow_plain_http", "router_credential", "router_credential_sealed"})
    if unknown:
        raise ConfigFileError(f"unknown key {unknown[0]!r}")
    settings = FileSettings()
    for key in ("rogue_dhcp", "router_igd", "router_login", "router_allow_plain_http"):
        if key in document:
            if not isinstance(document[key], bool):
                raise ConfigFileError(f"{key} must be true or false")
            setattr(settings, key, document[key])
    if "allow_dhcp" in document:
        allowed = document["allow_dhcp"]
        if not isinstance(allowed, list) or len(allowed) > MAX_ALLOWED or not all(isinstance(item, str) for item in allowed):
            raise ConfigFileError(f"allow_dhcp must be a list of at most {MAX_ALLOWED} addresses")
        for address in allowed:
            try:
                ipaddress.ip_address(address)
            except ValueError:
                raise ConfigFileError(f"allow_dhcp: {address!r} is not an address") from None
        settings.allow_dhcp = list(allowed)
    if "dhcp_interface" in document:
        name = document["dhcp_interface"]
        if not isinstance(name, str) or (name and not is_private_address(name)):
            raise ConfigFileError("dhcp_interface must be a private address of this machine, such as 192.168.0.10")
        settings.dhcp_interface = name
    _read_router(document, settings)
    return settings


def _read_router(document: dict, settings: FileSettings) -> None:
    if "router_kind" in document:
        if document["router_kind"] not in router_login.KINDS:
            raise ConfigFileError(f"router_kind must be one of {', '.join(router_login.KINDS)}")
        settings.router_kind = document["router_kind"]
    if "router_credential" in document:
        if document["router_credential"] not in router_login.STORES:
            raise ConfigFileError(f"router_credential must be one of {', '.join(router_login.STORES)}")
        settings.router_credential = document["router_credential"]
    for key, limit in (("router_user", 64), ("router_url", 200), ("router_credential_sealed", 512)):
        if key in document:
            value = document[key]
            if not isinstance(value, str) or len(value) > limit or not value.isprintable():
                raise ConfigFileError(f"{key} must be a short printable text")
            setattr(settings, key, value)
    if settings.router_url:
        why = router_login.check_url(settings.router_url, settings.router_kind, settings.router_allow_plain_http)
        if why:
            raise ConfigFileError(f"router_url: {why}")
    if settings.router_login and not settings.router_user:
        raise ConfigFileError("router_login needs router_user")


def load(path: Path, required: bool) -> FileSettings:
    """The settings in `path`. A file that is not there is the defaults, unless it was asked for by name (`required`)."""
    try:
        data = path.read_bytes()[: MAX_BYTES + 1]
    except FileNotFoundError:
        if required:
            raise ConfigFileError(f"{path} does not exist") from None
        return FileSettings()
    except OSError as error:
        raise ConfigFileError(f"{path} cannot be read ({error.strerror or error})") from None
    if len(data) > MAX_BYTES:
        raise ConfigFileError(f"{path} is larger than {MAX_BYTES} bytes")
    try:
        return parse(data.decode("utf-8"))
    except UnicodeDecodeError:
        raise ConfigFileError(f"{path} is not UTF-8") from None
