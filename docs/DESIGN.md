# Design of ARMOR-NETWORK

ARMOR-NETWORK watches the local network of the house: which devices are on it, what is known about each, whether the internet is there and, when it is not, whose fault it is, and what changes. It is a program (Python 3.11, standard library only) that runs on a machine of the network — a PC, the CM5, a Raspberry Pi — and tells ARMOR-SERVER; the server, Studio and the phone show it and raise the alarms. **It observes: it never configures a router or a device.**

```
  the machine's neighbour table ─┐
  echo and TCP to the devices ───┤                      ┌── ARMOR-SERVER ── alarms, history ── Studio (Network menu, Network Designer)
  mDNS, UPnP, NetBIOS, rDNS ─────┼── ARMOR-NETWORK ─────┤                                    └── Android (Network screen)
  echo, TCP, DNS, web to the ────┤   (inventory, events, └── armor/network/<node>/state (MQTT) or POST /api/v1/network/state
  router and the internet ───────┘    internet state)
```

## What it looks at

| What | How | Sends to the network |
|---|---|---|
| Who is there | the system's neighbour table (`arp -a`, `/proc/net/arp`), filled by a one-byte UDP datagram to the discard port of every address, then one ICMP echo to each device found | ARP requests the system makes, an echo, a datagram |
| What each offers | a TCP connection to 17 (`quick`) or 44 (`standard`) ports, twelve at a time, reading at most a few hundred bytes (a banner, a web page's title) | a TCP handshake per port |
| What each says of itself | mDNS (`_services._dns-sd._udp.local`), SSDP (`M-SEARCH`), the description a UPnP device publishes, a NetBIOS name request, the system's reverse DNS | the multicast questions, one request each |
| Who made it | the first three bytes of the MAC in the IEEE register (`data/oui.tsv.gz`, 40,250 blocks); a locally administered (random) MAC has no maker and is not an identity | nothing |
| The internet | every few seconds: an echo (or TCP) to the router, a TCP connection to 1.1.1.1:443, DNS questions to 1.1.1.1 and 8.8.8.8, a web page (`generate_204`) | those, to public addresses; the only traffic that leaves the private range |
| Traffic | the counters of the interface (`/proc/net/dev`; `netstat -e` on Windows, the sum of the interfaces) | nothing |

## The inventory and its events

A device is its MAC (lowercase, with colons) or, until the MAC is learned, `ip-<address>`. `Inventory.observe` folds a round of observations into what is known and returns what changed:

* `new_device`: never seen before. **The first scan of a new inventory only learns** (the baseline), so the first run does not report every device of the house.
* `device_offline` after `offline_after` (180 s) without an answer, and `device_online` when it returns. While the router does not answer, nobody is called offline: a device that is not seen is not a device that is gone.
* `ip_changed`: the same MAC at another address (a DHCP lease).
* `arp_conflict`: an address answered by another MAC while its last owner is still on the network, or the router's address answered by another MAC at all. Told once an hour for the same pair.
* `port_opened` / `port_closed`, once the ports of that device have been seen once.

Events keep an id that never repeats (kept across restarts, in `inventory.json`), and the message repeats the last 64, so the server tells each one once whichever number of times it reads it.

## The internet

`InternetMonitor` turns rounds into a state: `up`, `degraded`, `down` (the router answers and nothing beyond it does: **the provider's side**), `lan_down` (the router does not answer either: **this side**) or `unknown`. Three rounds in a row without any answer make an outage and two good rounds end it; the outage is dated from its first failed round and counted to the first good one; degraded has a margin (goes bad at 20 % loss or 300 ms, well again below 10 % and 200 ms) so a value on the edge does not flap. Loss is the share of rounds in the last minute in which fewer than half of the probes answered, so one place that never answers (a blocked DNS) is not loss. The outages are kept in `internet.json` for the totals of the last 24 hours; the time this program is not running is not counted as an outage.

## The message and where it goes

`armor/network/{node_id}/state`, contract `network.schema.json` of ARMOR-COMMON (see [MESSAGES.md](MESSAGES.md)). `timestamp_ms` and every `*_ms` are milliseconds since 1970: this node is a program with a real clock. The kind of a device, its system and its maker are labelled as guesses in the contract.

## The real network and the scripted one

The agent knows the network only through a `NetworkIO`: `SystemIO` (the real machine: `system_io.py`) or `SimIO` (`sim_io.py`, a house with an unknown device that joins with Telnet open, a camera that opens Telnet, a smart plug that goes and comes back, an internet outage with the router answering, a local outage, and someone answering for the router). The tests and `demo` use the second; nothing in them touches a network.

## What it does not do

* It does not capture packets (no raw sockets, no drivers): it cannot see who talks to whom, and traffic per device or intrusion detection in the strict sense (port scans against the house, attacks) needs the router's counters, its logs or a mirror port. That is a later step and depends on the router.
* It does not control anything: no blocking of a device, no closing of a port, no change to the router. Marking a device as known is a note on the server.
* Presence has minutes of lag: a phone that sleeps still answers ARP, and the system keeps a neighbour for a while after it has gone.
* Every result about what a device is (kind, system, maker) is a guess from an address, some answers and a register.
* It has been run once on a real network that had a router and a phone on it; it has not watched a whole house for days.
