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
| `--cidr` | the network to scan when it is not the one of the default route; always private and at most a /22 |
| `--profile quick\|standard` | 17 or 44 ports per device (default `quick`) |
| `--no-ports` | do not look at ports at all |
| `--skip IP` | never probe this address (repeatable) |
| `--data-dir` | where the inventory and the outages are kept between runs (default `armor-network-data`) |
| `--scan-every`, `--internet-every` | seconds between sweeps (60) and internet checks (5) |
| `--count N` | stop after N messages (0: never) |
| `--no-public-info` | do not ask a public service for the public address |
| `--public-info-url URL` | the https service that tells it (default `https://ipinfo.io/json`) |

## Running it for good

On the machine that is always on (the CM5, a Raspberry Pi, a PC): a systemd unit or a scheduled task that runs `armor-network watch` with the server's address, and `--data-dir` in a folder that survives reboots. The server needs the node to be allowed to write `armor/network/<node>/state` if it uses MQTT (`scripts/mqtt_identity.sh add network-node <node>` in ARMOR-DEVOPS); over HTTP it only needs the ingest token.

A unit that works (the user, the paths and the server address are examples):

```ini
[Unit]
Description=A.R.M.O.R. Network local monitor
After=network-online.target
Wants=network-online.target

[Service]
User=armor
WorkingDirectory=/opt/armor/apps/ARMOR-NETWORK
Environment=PYTHONPATH=/opt/armor/apps/ARMOR-NETWORK/src
EnvironmentFile=/opt/armor/etc/armor.env
ExecStart=/usr/bin/python3 -m armor_network watch --node-id house-1 --server-url http://127.0.0.1:18080 --data-dir /opt/armor/data/network-watch
Restart=on-failure
RestartSec=5
MemoryMax=128M
TasksMax=256

[Install]
WantedBy=multi-user.target
```

Keep `TasksMax` at 256 or more: a sweep runs up to 32 `ping` workers, each starting a `ping` process of its own, and 12 more for the ports, so a smaller limit (32 is a common one) kills the node at its first sweep with `can't start new thread`. `ARMOR_INGEST_TOKEN` comes from the environment file, so it is never on a command line. When the server runs over HTTPS with a certificate for a host name, give `--server-url` that name (the certificate is checked, and a bare address does not match it); on the server's own machine, point the name at `127.0.0.1` in `/etc/hosts`.

## What to expect

The first scan of a fresh `--data-dir` only learns: nothing is reported as new. From then on a device that appears is a `new_device` event and, on the server, an alarm until an administrator marks it as known in Studio. On Windows the sweep takes 10 to 20 seconds; a device that sleeps still answers ARP, so it stays present, and one that leaves is called offline after three minutes.

The made-up house of `demo` plays its script on a clock of its own (`--tick-s`, ten seconds by default): in the first minutes an unknown device joins, a camera opens Telnet and a smart plug goes and comes back; then the internet goes down and back, the whole local network goes down and back, and someone starts answering for the router.
