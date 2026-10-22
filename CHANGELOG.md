# Changelog

All notable changes to this project are documented here.

## [Unreleased]

- The banner follows the animated style of the ecosystem banners, with the name, the kind and the technologies of the project.
- Looking at the web page of a device closes the answer of a refusal once it has been read, and the test of the login that is not sent to a device whose certificate changed no longer leaves one open; the whole suite passes with unclosed resources treated as errors.

## [0.1.3] - A large network is looked at as the /24 of this machine, and a down server is retried less often

- On a network larger than a /22 (an office /16, a home mesh) the node no longer refuses to start: it looks at the /24 its own address is in, and the `internet` command works there. A network named with `--cidr` is still checked as before.
- When the server cannot be reached the node waits longer between tries (10 s, then 20, 40, 80, 160 and at most 5 minutes) and says in the log when the next one is; one success goes back to the normal pace.

## [0.1.2] - A broken saved file, a name that only looks like this machine and a bad address no longer end in a traceback

- A saved public-address file that holds valid JSON that is not an object (a list, a number) no longer stops the watcher at start: it is forgotten like any damaged file.
- A server address that starts with `127.` but is a name (`127.evil.example`) was taken for this machine, so the warning about plain HTTP across the network was skipped for it; only a real loopback address counts now.
- A bad `--server-url` (a login or a path in it) or a bad `--public-info-url` is said as a message with exit code 2 instead of a Python traceback.
- The real system layer, the manual orders and the command line have tests of their own (the probes are replaced, nothing touches a network): 167 tests.

## [0.1.1] - Logins that are never opened in the clear, and a service that keeps up with its network

- **A saved login is not opened over plain HTTP across the network:** the seal is keyed with the token the node sends in clear, so anyone who saw one request could open it. The node now opens a login only when the server is `https://` or on the same machine; otherwise the `inspect` says the login was not used. USAGE explains the node's own token and a hardened unit with its own environment file.
- **The certificate is checked in the same connection that carries the login** (after the handshake, before any header): a certificate that is not the kept one, or that cannot be read, sends nothing. Before, it was read in one connection and the login sent in another, and an unreadable certificate let the login go.
- **The login goes only to the machine it belongs to:** if the address is answered by another MAC than the device's, or two machines claimed it in the last ten minutes, the saved login is not used.
- **Redirects:** the web look at a device (`http`) and the UPnP description are followed only to private addresses; 8883 (MQTT over TLS) is no longer fetched as a web page.
- **The interface is read again every minute** (a renewed lease, a moved cable or a changed router no longer leave the node on the old address until a restart); a moment without a route keeps the last one.
- **The disk:** the internet history and the inventory are written once a minute unless something happened (not every 5 and 10 seconds, which wears a memory card), and a disk that cannot be written no longer stops the program. A damaged inventory is kept aside as `inventory.json.corrupt-<time>`.
- **The first three sweeps only learn** (the first one often sees only part of the network, and the rest came out as new devices).
- A default route without a gateway (`default dev wwan0`) is accepted, and with several the lowest metric wins; `--node-id` is validated (the server refused every message of a bad one); makers are matched by whole words ("zte" is no longer "Aztech") and generic city names no longer make a device an IoT thing; `tools/fetch_oui.py` does not overwrite the table with an incomplete download.
- The documents say what is true (89 to 93 tests, no MQTT client, the node's own token, who writes the unit). Tests: 93 (4 new: the plain-HTTP rule, the MAC and conflict rule, routes, whole-word makers; the certificate test follows the new check).

## [0.1.0] - The login goes only to the device it was first sent to

- When a device is looked at over HTTPS with a login, the certificate it shows is kept the first time (trust on first use) in a private file (`~/.armor-network/https-pins.json`, or the path in `ARMOR_NETWORK_PINS`).
- If the certificate of that address later is another one (another device, or someone in the path pretending to be it), the login is not sent and the result says so; removing the line from the file accepts the new certificate.
- Tests cover the store (new, same, changed, damaged file) and that the login reaches only the device first seen.

## [0.0.9] - The login of an inspection arrives sealed

- The node opens the login of an inspection order with its own token (`auth_sealed`); one that does not open, or a message for another node, leaves the order without a login.
- A test checks the format against a vector produced by the server.

## [0.0.8] - Basic authentication only over HTTPS, and an agent that does not repeat finished orders

- The agent sends Basic credentials only over HTTPS unless a flag allows plain HTTP, and the command line warns when the address is not local.
- An order that already finished is not run again after the agent restarts.
- Tests cover both.

## [0.0.7] - Sturdier agent, inventory and orders

- Hardening of the agent, the inventory, the system access and the orders, with tests.

## [0.0.6] - Look at a device's web login

- **`inspect` order:** with the login the person gave for that one order, the node opens the device's web administration (Basic or Digest), says whether it asks for a login, whether the login is accepted, whether it is a factory login that should be changed, and what the page says about the device (server, title, model, firmware, serial number). One login, tried once; nothing is changed on the device, and the password never appears in any output, log or printout.
- Tests for the order, the parsing and the simulated device.
- Documentation: the seven READMEs describe the orders on request, and the message and safety documents describe `inspect`.
- **The calls that were too slow cannot pile up:** at most 32 of them are left running at once (a name server that never answers no longer accumulates threads), and the count falls as they end.
- **Tests for the real system layer** (`tests/test_system_io.py`): a quick call, one that fails, one that is too slow and counted until it ends, the cap, and the tools that are missing, too slow or print.

## [0.0.5] - The public address, and orders from Studio

- **The public address of the connection** (`public` in the message): every ten minutes the node asks a public service (`https://ipinfo.io/json` by default, `--public-info-url` to change it, `--no-public-info` to stop) and reports the address, the provider and the city, and when the address was seen to change. The answer is reduced to a real address and short plain texts; it is the one request this program makes that leaves the house, and nothing about the house is in it.
- **Manual orders** (`results` in the message): an operator can ask from Studio for a sweep right now, a ping, a traceroute, a wake-up packet, a look at the ports of a device or at its web page. The orders arrive in the answer to the node's own message (the node never listens), at most four at a time, and each is checked before anything is done: one of six kinds, an address that is private, on the network the node watches, not its own and not one it was told to skip; a wake-up goes to the broadcast of that network only; nothing runs through a shell; an order that does not pass is answered with the reason. Results go out in every message for two minutes.
- 13 new tests (66 in all); `docs/SAFETY.md`, `docs/MESSAGES.md`, `docs/USAGE.md` and the seven READMEs say what leaves the house and what comes in.

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
