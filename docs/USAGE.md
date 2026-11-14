# Using ARMOR-NETWORK

Python 3.11 or newer, nothing to install: `PYTHONPATH=src python -m armor_network ...` from the project, or `pip install .` and `armor-network ...`.

```bash
armor-network scan                       # look once and print: the interface, the internet, every device with its ports
armor-network scan --json                # the message itself
armor-network internet                   # three rounds of the internet check; exit status 0 when it is up
armor-network oui 24:0a:c4:11:22:33      # who made a network card
armor-network watch --server-url http://192.168.0.10:18080 --ingest-token ...      # keep watching and tell ARMOR-SERVER
armor-network demo --count 3 --validate  # a made-up house; --validate checks every message against ARMOR-COMMON
```

`--server-url` and `--ingest-token` go together (the token can also be the environment variable `ARMOR_INGEST_TOKEN`, so it never has to be written on a command line or in a file). Without them, `watch` and `demo` print one message per line.

## Options

| Option | Meaning |
|---|---|
| `--node-id` | the name of this node in the messages (default `network-1`) |
| `--cidr` | the network to scan when it is not the one of the default route; always private and at most a /22; without it, a larger network is reduced to the /24 of this machine |
| `--profile quick\|standard` | 17 or 44 ports per device (default `quick`) |
| `--no-ports` | do not look at ports at all |
| `--skip IP` | never probe this address (repeatable) |
| `--data-dir` | where the inventory and the outages are kept between runs (default `armor-network-data`) |
| `--scan-every`, `--internet-every` | seconds between sweeps (60) and internet checks (5) |
| `--count N` | stop after N messages (0: never) |
| `--no-public-info` | do not ask a public service for the public address |
| `--mqtt-url URL` and `--mqtt-user NAME` | also publish every message to this MQTT broker (`mqtt://` or `mqtts://`, on `armor/network/<node>/state`, one short connection per message, QoS 0); the password is read from `ARMOR_NETWORK_MQTT_PASSWORD`, never from an argument. The manual orders of Studio travel in the answer of the server's route and not over MQTT, so a node that publishes only here does not receive them |
| `--dhcp-interface IP` | the private address of this machine, on the interface to look from, that the DHCP question of `--rogue-dhcp` is bound to (default: the address of the interface the default route leaves by); the socket is never bound to every interface: on Linux it is tied to the device and listens on the broadcast address, elsewhere it is bound to that address |
| `--rogue-dhcp` | look for a second DHCP server: one DHCP question on the broadcast address every ten minutes (nothing is leased); off by default, and it needs permission to use the DHCP client port (without it the answer is simply no finding) |
| `--allow-dhcp IP` | a DHCP server that belongs on the network besides the router; repeatable |
| `--router-igd` | read the traffic counters of the router over UPnP (no login, read only); off by default |
| `--dns-name NAME` | the name the house is reached by from outside (the dynamic DNS name): each time the public address is asked for, the node resolves it and the message says whether it points to that address, so the server can warn when the address changed and the name did not follow. Resolve it from the house to the public address (a name that the house resolves to a private address never matches) |
| `--public-info-url URL` | the https service that tells it (default `https://ipinfo.io/json`) |

## Running it for good

On the machine that is always on (the CM5, a Raspberry Pi, a PC): a systemd unit or a scheduled task that runs `armor-network watch` with the server's address, and `--data-dir` in a folder that survives reboots. The server needs the node to be allowed to write `armor/network/<node>/state` if it uses MQTT (`scripts/mqtt_identity.sh add network-node <node>` in ARMOR-DEVOPS); over HTTP it only needs the ingest token.

On a CM5 bench the unit, the token file and the user are created for you by `scripts/install_cm5.sh --with-network` in ARMOR-DEVOPS (dry run by default, `--apply` installs). To install it by hand, this is a unit that works (the user, the paths and the server address are examples):

```ini
[Unit]
Description=A.R.M.O.R. Network local monitor
After=network-online.target
Wants=network-online.target

[Service]
User=armor
WorkingDirectory=/opt/armor/apps/ARMOR-NETWORK
Environment=PYTHONPATH=/opt/armor/apps/ARMOR-NETWORK/src
EnvironmentFile=/opt/armor/etc/armor.network-node.env
ExecStart=/usr/bin/python3 -m armor_network watch --node-id house-1 --server-url http://127.0.0.1:18080 --data-dir /opt/armor/data/network-watch
Restart=on-failure
RestartSec=5
MemoryMax=128M
TasksMax=256
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/opt/armor/data/network-watch
CapabilityBoundingSet=

[Install]
WantedBy=multi-user.target
```

Keep `TasksMax` at 256 or more: a sweep runs up to 32 `ping` workers, each starting a `ping` process of its own, and 12 more for the ports, so a smaller limit (32 is a common one) kills the node at its first sweep with `can't start new thread`. `ARMOR_INGEST_TOKEN` comes from its own small environment file (`/opt/armor/etc/armor.network-node.env`, mode 0640, `root:armor`, one line: `ARMOR_INGEST_TOKEN=<this node's own token>`), so it is never on a command line, and this process - which reads hostile data from the network - does not get the server's other secrets (it must not read `armor.env`). The node's own token (Studio shows it for `node_id`) is the one the server needs to hand this node a saved login for `inspect`; the shared ingest token works for delivering the state, but an `inspect` then arrives without a login (and with `ARMOR_INGEST_STRICT=1` the shared token is refused).

A saved login is sealed with that token, which the node sends in clear in every request, so over plain `http://` across the network anyone who saw one request could open it: **the node never opens a login unless the server's address is `https://` or this same machine** (an `inspect` then says the saved login was not used). `--server-url http://127.0.0.1:...` as above is fine. When the server runs over HTTPS with a certificate for a host name, give `--server-url` that name (the certificate is checked, and a bare address does not match it); on the server's own machine, point the name at `127.0.0.1` in `/etc/hosts`.

## What to expect

The first three sweeps of a fresh `--data-dir` only learn: nothing is reported as new (the first one often sees only part of the network). From then on a device that appears is a `new_device` event and, on the server, an alarm until an administrator marks it as known in Studio. On Windows the sweep takes 10 to 20 seconds; a device that sleeps still answers ARP, so it stays present, and one that leaves is called offline after three minutes.

The made-up house of `demo` plays its script on a clock of its own (`--tick-s`, ten seconds by default): in the first minutes an unknown device joins, a camera opens Telnet and a smart plug goes and comes back; then the internet goes down and back, the whole local network goes down and back, and someone starts answering for the router.

## Findings, a second DHCP server and the router's counters (building blocks, off by default)

* **Findings** (`findings.py`): `risky_port_findings` turns the open risky ports of the inventory (FTP, Telnet, SMB, the databases, remote desktop, TR-069) into findings with a stable id, a severity and a recommendation key; `rogue_dhcp_findings` does the same for a DHCP server that should not be there. A finding is a statement, never an action: the node closes and blocks nothing.
* **A second DHCP server** (`rogue_dhcp.py`, opt-in, off by default): one DHCPDISCOVER to the broadcast address with a random transaction, and every DHCPOFFER that answers it is read (the server, the address offered, the gateway, the DNS servers); the node never answers an offer with a request, so no address is taken. `judge` reports every server that is not the gateway or one the person named, once. The module builds and reads packets; the socket is in `system_io.py` (`--rogue-dhcp`, `--allow-dhcp`), which asks every ten minutes and tells each server once as a `rogue_dhcp` event.
* **The router's counters** (`igd.py`, opt-in, off by default): the bytes the router has carried, asked as a UPnP Internet Gateway Device (`GetTotalBytesReceived` and `GetTotalBytesSent`), with no login and nothing written; only a private address on the host that answered the discovery is ever asked, and only the two read-only actions can be built. Leases and names of the devices need the router's credentials (TR-064 or OpenWrt) and are not part of this. With `--router-igd` the rates in the message come from these counters when the router answers, and from the system counters when it does not.

Joining them to the message of the node (the finding kinds in the contract, the labels in the server and Studio in eight languages) and the socket that sends the discover are the next steps, listed in the changelog.
