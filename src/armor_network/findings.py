"""What the network says that deserves a look: the risky ports that are open and the DHCP servers that should not be there, each with a recommendation.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

A finding is a statement about the network, never an action: the node does not close a port or block a server. Each one has a stable `id` (the same finding is the same id on every round, so
a consumer shows it once), a `severity` (`warning` or `info`), the device it is about when there is one, and a short `recommendation` key that the server and Studio write in the language of
the person. This module only turns what the inventory and the checks have already found into that list.
"""
from __future__ import annotations

from .services import RISKY_PORTS, SERVICE_NAMES

#: Why each risky port is a risk and what to do, as a key the consumers translate.
RECOMMENDATIONS = {
    21: "close_ftp", 23: "close_telnet", 445: "restrict_smb", 3306: "restrict_database", 3389: "restrict_remote_desktop", 5432: "restrict_database", 5900: "restrict_remote_desktop",
    6379: "restrict_database", 7547: "close_tr069",
}
assert set(RECOMMENDATIONS) == set(RISKY_PORTS), "every risky port has a recommendation"
MAX_FINDINGS = 64


def risky_port_findings(devices: list[dict]) -> list[dict]:
    """One finding per open risky port per device: {"id", "kind": "risky_port", "severity", "device_id", "port", "service", "recommendation"}. A device shows `ports` as the inventory gives them."""
    found: list[dict] = []
    for device in devices:
        device_id = device.get("id")
        ports = device.get("ports")
        if not isinstance(device_id, str) or not isinstance(ports, list):
            continue
        for entry in ports:
            port = entry.get("port") if isinstance(entry, dict) else entry
            if isinstance(port, bool) or not isinstance(port, int) or port not in RISKY_PORTS:
                continue
            found.append({"id": f"risky_port:{device_id}:{port}", "kind": "risky_port", "severity": "warning", "device_id": device_id, "port": port,
                          "service": SERVICE_NAMES.get(port, ""), "recommendation": RECOMMENDATIONS[port]})
    return sorted(found, key=lambda item: item["id"])[:MAX_FINDINGS]


def rogue_dhcp_findings(rogue: list[dict]) -> list[dict]:
    """The findings of `rogue_dhcp.judge`, with an id that is stable for the server."""
    return [{"id": f"rogue_dhcp:{item['server']}", "kind": "rogue_dhcp", "severity": "warning", "server": item["server"], "offered": item.get("offered"),
             "recommendation": "find_the_dhcp_server"} for item in rogue if isinstance(item.get("server"), str)][:MAX_FINDINGS]


def all_findings(devices: list[dict], rogue: list[dict] | None = None) -> list[dict]:
    return (risky_port_findings(devices) + rogue_dhcp_findings(rogue or []))[:MAX_FINDINGS]
