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

## Running it for good

On the machine that is always on (the CM5, a Raspberry Pi, a PC): a systemd unit or a scheduled task that runs `armor-network watch` with the server's address, and `--data-dir` in a folder that survives reboots. The server needs the node to be allowed to write `armor/network/<node>/state` if it uses MQTT (`scripts/mqtt_identity.sh add network-node <node>` in ARMOR-DEVOPS); over HTTP it only needs the ingest token.

## What to expect

The first scan of a fresh `--data-dir` only learns: nothing is reported as new. From then on a device that appears is a `new_device` event and, on the server, an alarm until an administrator marks it as known in Studio. On Windows the sweep takes 10 to 20 seconds; a device that sleeps still answers ARP, so it stays present, and one that leaves is called offline after three minutes.

The made-up house of `demo` plays its script on a clock of its own (`--tick-s`, ten seconds by default): in the first minutes an unknown device joins, a camera opens Telnet and a smart plug goes and comes back; then the internet goes down and back, the whole local network goes down and back, and someone starts answering for the router.
