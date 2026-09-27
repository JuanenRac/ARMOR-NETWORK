# Changelog

All notable changes to this project are documented here.

## [0.0.1] - The local network, watched

- **A program that looks at the network it is on** (Python 3.11, standard library only): the devices (the system's neighbour table filled by a poke of every address, an echo to each device found, a TCP look at 17 or 44 ports twelve at a time, and what devices announce about themselves by mDNS, UPnP and NetBIOS), the maker of each from the IEEE register of 40,250 blocks (`tools/fetch_oui.py` refreshes it), a guess of what it is (kind and system) and when it was first and last seen.
- **The inventory and what changes:** a device that appears (the first scan of a new inventory only learns), goes quiet or returns, changes its address, a port that opens or closes, and two machines answering for one address (the router's above all). Events keep ids that never repeat, across restarts. While the router does not answer nobody is called offline.
- **The internet check:** an echo to the router, a TCP connection, two DNS questions to chosen resolvers and a web page every few seconds; a state (`up`, `degraded`, `down` for the provider's side, `lan_down` for this side), latency and loss, and the outages, dated from their first failed round, kept between runs, with the totals of the last 24 hours.
- **The guard:** it refuses any address that is not private and any range larger than a /22; `--skip` keeps it from touching what is fragile; a slow name lookup is left behind. Nothing is sent to a device that is not an echo, a connection to a port, a multicast question or a name request.
- **The message `armor/network/{node}/state`** of ARMOR-COMMON 0.2.5, checked against the shared vectors; `scan` prints the network, `watch` tells ARMOR-SERVER (over HTTP with the ingest token), `demo` plays a made-up house without touching any network, `oui` says who made a card.
- 53 tests: the parsers against real samples (`ipconfig`, `route print`, `arp -a` in Spanish and English, `ping` in several languages, `netstat`, `/proc`), the DNS reader against hostile messages, the guard, the inventory and its events, the internet state machine, the whole agent against a scripted house (every message accepted by ARMOR-COMMON), the publisher against a stand-in server and the command line.
- **Not yet:** the router's counters (traffic per device), packet capture, controlling anything, and weeks on a real network.
