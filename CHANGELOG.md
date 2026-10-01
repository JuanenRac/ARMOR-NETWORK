# Changelog

All notable changes to this project are documented here.

## [0.0.4] - A healthy line no longer looks slow

- The latency of the line is what a ping, a connection and a DNS answer take. The web-page probe (a TLS handshake, a redirect, the other end's own load) is often a few hundred ms on a perfectly good line and was counted in the median, which made a healthy connection look degraded (32 'slow or lossy' alarms in three days on a line that was fine). It is still checked for being reachable, just not timed as the line.

## [0.0.3] - Running it for good, as a systemd service

- `docs/USAGE.md` now shows a working systemd unit and the one limit that matters in it: a sweep runs up to 32 `ping` workers, each starting a `ping` process of its own, plus 12 port workers, so a unit with a small `TasksMax` (32 is common) dies at the first sweep with `can't start new thread`; 256 is enough. Found for real the first time it was installed on the CM5.
- The MAC of the interface is read from `/sys/class/net/<interface>/address` with the file closed again (it was left to the garbage collector, a `ResourceWarning` in every test run on Linux).

## [0.0.2]

- A GitHub Actions CI baseline (`.github/workflows/ci.yml`): validates the manifest, the version, CHANGELOG.md's heading, the seven README translations' structure and its own local Markdown links, then runs this project's real build/test through `tools/armor_project_tool.py build-test .` (vendored from ARMOR-COMMON, alongside `tools/armor_ci_validate.py` and `tools/_armor_readme_parity.py`, which do the manifest/docs checking).

## [0.0.1] - The local network, watched

- **A program that looks at the network it is on** (Python 3.11, standard library only): the devices (the system's neighbour table filled by a poke of every address, an echo to each device found, a TCP look at 17 or 44 ports twelve at a time, and what devices announce about themselves by mDNS, UPnP and NetBIOS), the maker of each from the IEEE register of 40,250 blocks (`tools/fetch_oui.py` refreshes it), a guess of what it is (kind and system) and when it was first and last seen.
- **The inventory and what changes:** a device that appears (the first scan of a new inventory only learns), goes quiet or returns, changes its address, a port that opens or closes, and two machines answering for one address (the router's above all). Events keep ids that never repeat, across restarts. While the router does not answer nobody is called offline.
- **The internet check:** an echo to the router, a TCP connection, two DNS questions to chosen resolvers and a web page every few seconds; a state (`up`, `degraded`, `down` for the provider's side, `lan_down` for this side), latency and loss, and the outages, dated from their first failed round, kept between runs, with the totals of the last 24 hours.
- **The guard:** it refuses any address that is not private and any range larger than a /22; `--skip` keeps it from touching what is fragile; a slow name lookup is left behind. Nothing is sent to a device that is not an echo, a connection to a port, a multicast question or a name request.
- **The message `armor/network/{node}/state`** of ARMOR-COMMON 0.2.5, checked against the shared vectors; `scan` prints the network, `watch` tells ARMOR-SERVER (over HTTP with the ingest token), `demo` plays a made-up house without touching any network, `oui` says who made a card.
- 53 tests: the parsers against real samples (`ipconfig`, `route print`, `arp -a` in Spanish and English, `ping` in several languages, `netstat`, `/proc`), the DNS reader against hostile messages, the guard, the inventory and its events, the internet state machine, the whole agent against a scripted house (every message accepted by ARMOR-COMMON), the publisher against a stand-in server and the command line.
- **Not yet:** the router's counters (traffic per device), packet capture, controlling anything, and weeks on a real network.
