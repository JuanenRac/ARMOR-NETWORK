"""The settings of the checks that are off by default, kept in a file (`config.json` in the data directory, or the file given with `--config`).

Every key is optional and the default of each is "off". The flags of the command line win over the file: a flag that is given is used, one that is not is read from the file.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

    {
      "rogue_dhcp": false,        look for a second DHCP server (one DHCP question on the broadcast address every ten minutes; nothing is leased)
      "allow_dhcp": [],           DHCP servers that belong on the network besides the router
      "router_igd": false,        read the traffic counters of the router over UPnP (no login, read only)
      "dhcp_interface": ""        the private address of this machine, on the interface to look from, that the DHCP question is bound to (empty: the interface the default route leaves by)
    }
"""
from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass, field
from pathlib import Path

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


def parse(text: str) -> FileSettings:
    try:
        document = json.loads(text)
    except ValueError as error:
        raise ConfigFileError(f"not valid JSON ({error})") from None
    if not isinstance(document, dict):
        raise ConfigFileError("the file must hold one JSON object")
    unknown = sorted(set(document) - {"rogue_dhcp", "allow_dhcp", "router_igd", "dhcp_interface"})
    if unknown:
        raise ConfigFileError(f"unknown key {unknown[0]!r}")
    settings = FileSettings()
    for key in ("rogue_dhcp", "router_igd"):
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
    return settings


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
