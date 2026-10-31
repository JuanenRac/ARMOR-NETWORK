<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-NETWORK banner" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  🇺🇸 <b>English</b> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Watches the local network: the devices on it, whether the internet is there, what changes and what is new (a Python program with no dependencies; it runs on a machine of the network and reports to ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-187%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Honesty check - what runs today:** The scanner, the inventory that tells what changed, the internet check, the public-address look-up, the orders from Studio and the sealed logins are tested on a computer against a scripted network (187 tests; every message is accepted by ARMOR-COMMON's contract), and the program runs as a service on the CM5 test bench, watching the real network the bench is on (a router, the phones and nodes of the house). It has not watched a whole house for weeks, it only asks the router and never configures it, and what a device is (its kind, its system, its maker) is a guess. It does not capture packets: it cannot see who talks to whom, and traffic per device and intrusion detection in the strict sense need the router's counters or a mirror port, which is a later step.

---

## 📋 At a glance

| | |
|---|---|
| Version | `0.1.5` |
| Maturity | Established |
| Role | Local network node: what is on the network, what changed, the internet, orders from Studio |
| Stack | Python 3.11+, standard library only |
| Tests | 187 (`python -m unittest discover -s tests`) |
| Contract | Message `armor/network/<node>/state`, 111 conformance vectors (messages and orders) |
| Runs on | A machine of the network to be watched (Linux, Windows or macOS); the CM5 test bench as a service |
| On real hardware | Runs as a service on the CM5 test bench, watching its real network (a router, the phones and nodes of the house) |
| License | GPL-3.0-or-later |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Security](#-security--safety) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Quick start](#-quick-start) · [Testing](#-testing) · [Troubleshooting](#-troubleshooting) · [Structure](#-repository-structure) · [Related](#-related-projects)

## 🚦 Project status

Each line is one part of this repository and the light says how far it is today. It is written from what the repository can show (tests, builds, runs), not from what is planned.

🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working

| Area | State | What it means here |
|---|---|---|
| Software | 🟢 | The scanner, the inventory that tells what changed, the internet check, the public-address look-up and the orders from Studio run as a service on the CM5 test bench. |
| Tests | 🟢 | 187 tests pass against a scripted network, and every message is accepted by the contract of ARMOR-COMMON. |
| Protocols and data | 🟡 | What a device is (its kind, its system, its maker) is a guess, and nothing captures packets: traffic per device and intrusion detection in the strict sense are not done. |
| Hardware | 🟡 | It watches the real network of the CM5 test bench (a router, the phones and nodes of the house) but has not watched a whole house for weeks. |
| Security | 🟡 | It only asks the router and never configures it; the sealed logins are tested on the host, and there has been no independent review. |
| Integration | 🟡 | Its messages reach the CM5 test bench server and Studio; the commands from Studio are tested against a scripted network. |
| Documentation | 🟢 | Eight languages and the changelog are up to date. |

## 🎯 Overview

* **What is on the network:** the neighbour table of the machine, a poke of every address so that it fills, an echo to each device found (latency and TTL) and what devices announce about themselves (mDNS, UPnP, NetBIOS, reverse DNS). For each device: address, MAC, maker (from the IEEE register of 40,000 blocks), name, kind, system, open ports with what each says, and when it was first and last seen.
* **Ports:** a TCP connection to 17 (or 44) ports of each device, twelve at a time, reading at most a few hundred bytes of what answers; never a login, never an exploit. A new device is looked at at once, the others every quarter of an hour.
* **What changes:** a device that appears (the first three sweeps only learn), goes quiet or comes back, changes its address, a port that opens or closes, and two machines answering for one address (the router's above all). Every event has an id, so it is told once.
* **The internet:** every few seconds an echo to the router, a TCP connection, two DNS questions to chosen resolvers and a web page. An outage takes three rounds to be called one and two to be over, is dated from its first failed round and counted to the first good one, and says whose fault it is: the provider's (the router answers and nothing beyond it does) or this side's (the router does not answer either). Latency, loss and the outages of the last 24 hours.
* **It only looks at your own network:** it refuses any address that is not private (10/8, 172.16/12, 192.168/16) and any range larger than a /22; a skip list keeps it away from what is fragile; nothing is sent to a device that is not a question.
* **The message** `armor/network/<node>/state`: the interface, the internet, every device and the latest events; it is in the shared contract (111 vectors) and carries findings, never commands. `python -m armor_network scan` prints it as a table, `watch` tells ARMOR-SERVER, `demo` plays a made-up house (a new device joins, a camera opens Telnet, the internet falls and comes back, someone answers for the router) without touching any network.
* **Where it shows:** the Network menu of ARMOR-STUDIO (the devices, the internet with its outages and latency, the traffic and the events; an administrator names devices and marks the known ones, which quiets the alarm of a new device), the Network Designer (the drawing of the house's network, compared with what was found, and able to draw it) and the Network screen of the Android app. ARMOR-SERVER raises the alarms.
* **Orders from Studio:** a sweep now, a ping, a traceroute, a wake-up, the ports or the web page of one device and an inspection with a login you give; orders arrive in the answer to the node's own message (never as a connection made to the node), each is checked before anything is done, and nothing is run through a shell.
* **Logins that stay safe:** the login of an inspection travels sealed for this node alone, is sent only over Digest or HTTPS (never Basic over plain HTTP), only to the device whose HTTPS certificate was seen the first time, and is never echoed back.
* **The public side:** the house's public address, who gives it and where it is (one HTTPS request to a fixed public service every few minutes; `--no-public-info` turns it off). With `--dns-name` it also resolves the name the house is reached by from outside and says whether it points to that address.
* **A service:** it runs as a systemd unit on the CM5 test bench (written by hand, see the usage guide) and keeps its data in its own folder.
* **Not yet:** the router's own counters (traffic per device), packet capture, controlling anything (blocking a device, closing a port, changing the router) and weeks on a real network.

## 🧩 Role in A.R.M.O.R.

ARMOR-NETWORK is the family's eye on the local network. It runs on a machine of the network (the CM5 on the bench), looks at what is there without touching it and reports to [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER), which keeps the names, the hidden and watched devices and the outages; the *Network* menu and the *Network Designer* of [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) and the Network screen of [ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL) show it, and Studio can hand it orders. It never configures the router or any device.

| It talks to | How | What for |
|---|---|---|
| ARMOR-SERVER | HTTP `POST` with the ingest token (`--server-url`) | the state goes in; the orders come back in the answer |
| MQTT | `--mqtt-url` (`mqtt://` or `mqtts://`) | the same message also on the broker; the manual orders do not travel this way |
| ARMOR-STUDIO | through the server | the Network menu and the Network Designer show it and hand it orders |
| ARMOR-ANDROID-CONTROL | through the server | the Network screen |
| ARMOR-COMMON | the contract of the message and of the orders | `--validate` checks every message against it |

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-NETWORK architecture: the local network it looks at, the modules of the node and what it tells the server, Studio and the broker" width="100%">
</p>

## 🔒 Security & Safety

| Threat | Defence |
|---|---|
| Scanning outside the house or another network | Only private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) and never more than 1024 addresses (a /22); `--cidr` is always private; the guard is `check_scan_range`, not an option |
| Breaking something fragile | A skip list (`--skip IP`, repeatable); nothing is sent to a device that is not a question; never a login, never an exploit; 12 connections at a time reading a few hundred bytes |
| Risky open ports go unnoticed | They are marked: 21, 23, 3389, 5900, 6379, 3306, 5432, 7547 and 445 |
| Orders from the server that inject commands | A closed list: `scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`; at most 4 at a time; an order id of letters, digits, `_` and `-` (32 at most); output cut at 2000; MAC checked; nothing is run through a shell; orders arrive in the answer to the node's own message, never as a connection made to the node |
| The login of an inspection leaks | It travels sealed for this node alone, only over Digest or HTTPS (never Basic over plain HTTP), only to the device whose HTTPS certificate was seen the first time, and is never repeated in an answer; the factory logins it tries come from a fixed list |
| A request that leaves the house | One HTTPS request to a fixed public service (`https://ipinfo.io/json` by default) every few minutes, for the public address; `--no-public-info` turns it off; `--dns-name` also checks that the name the house is reached by points to it |

**What it never does:** configure the router, capture packets, block a device or close a port. What a device is (its kind, its system, its maker) is a guess. The safety notes are in [docs/SAFETY.md](docs/SAFETY.md); there has been no independent review.

## 🔌 Interfaces

| Route | Auth | What it does |
|---|---|---|
| `armor/network/<node>/state` | message | the interface, the internet, every device and the latest events; it carries findings, never commands |
| `python -m armor_network scan [--json]` | - | look at the network once and print it as a table (or as the message) |
| `python -m armor_network watch` | - | keep watching; with `--server-url` and `--ingest-token` it tells ARMOR-SERVER, with `--mqtt-url` also the broker |
| `python -m armor_network demo [--count N]` | - | a made-up house (a device joins, a camera opens Telnet, the internet falls): nothing on any network is touched |
| `python -m armor_network internet`  `oui <mac>` | - | one round of the internet check; who made a network card |

The orders from Studio (`scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`) are queued by the routes `/api/v1/network/...` of ARMOR-SERVER and reach the node in the answer to its message; the contract of the message and of the orders is in ARMOR-COMMON (111 conformance vectors). See [docs/MESSAGES.md](docs/MESSAGES.md) and [docs/USAGE.md](docs/USAGE.md).

## ⚙️ Configuration

| Setting | Default | What it does |
|---|---|---|
| `--node-id` | network-1 | the name of this node in the messages (lowercase letters, digits, `-` and `_`) |
| `--profile {quick,standard}` | quick | 17 or 44 ports per device; a new device is looked at at once, the others every quarter of an hour |
| `--no-ports`  `--skip IP`  `--cidr` | - | no ports at all; an address never to probe; the network to scan (private, at most 1024 addresses) |
| `--scan-every`  `--internet-every` | 60 s  5 s | seconds between sweeps and between internet checks |
| `--server-url`  `--ingest-token`  `--mqtt-url`  `--mqtt-user` | - | where it tells; the token of this node (Studio shows it) or the shared ingest token, never written to a file |
| `--data-dir` | armor-network-data | where the inventory and the outages are kept between runs |
| `--validate`  `--no-public-info`  `--public-info-url`  `--dns-name` | - | check each message against ARMOR-COMMON; the public-address look-up (off, its address, the name to check) |

All of it is set by command-line flags (see [docs/USAGE.md](docs/USAGE.md), which also shows the systemd unit that keeps it running). An outage is called after three failed rounds and ended after two good ones; the first three sweeps only learn what is there.

## 🚀 Quick start

**Requirements:** Python 3.11+ (standard library only) and a machine on the network to be watched (Linux, Windows or macOS).

```powershell
python -m unittest discover -s tests                                                 # 187 tests: parsers with real samples, the guard on what may be probed, the inventory, the internet, the whole agent against a scripted house
python -m armor_network scan                                                         # look at the network once and print it (only the private network of this machine)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...  # keep watching and tell ARMOR-SERVER
python -m armor_network demo --count 3                                               # a made-up house: nothing on any network is touched
python tools/fetch_oui.py                                                            # refresh the table of makers from the IEEE register (a person runs it, now and then)
```

See the [usage](docs/USAGE.md) and the [design](docs/DESIGN.md).

## 🧪 Testing

```powershell
python -m unittest discover -s tests  # 187 tests
python -I tools/armor_ci_validate.py
```

| Test file | Tests | What it covers |
|---|---|---|
| `test_network.py` | 56 | the parsers with real samples, the guard on what may be probed, the inventory, the internet and the agent against a scripted house |
| `test_system_io_layer.py`  `test_system_io.py` | 39 | the real-network layer: neighbours, echoes, TCP, DNS |
| `test_orders.py`  `test_orders_edges.py` | 56 | the orders from Studio and their limits |
| `test_cli_commands.py` | 20 | the command line |
| `test_mqtt_out.py`  `test_seal.py` | 10 | the MQTT output and the sealed logins |
| `test_typing_behaviour.py` | 6 | the behaviour the type annotations keep: the scan guard, the order parser and the vendor tables |

GitHub Actions runs the A.R.M.O.R. baseline on every push and pull request: the validation of the manifest, version, changelog and README parity, then the project's own build and tests. The sources also pass the type checker: `python -m mypy` (configured in `pyproject.toml`) reports nothing, and `test_typing_behaviour.py` fixes the behaviour the annotations keep.

## 🏗️ Build & Release

It is plain Python: nothing to compile. The version lives in `pyproject.toml`, in `armor.project.json` and in the README badge (read from the manifest); each version has its entry in [CHANGELOG.md](CHANGELOG.md). Releases are published on GitHub.

## 🩺 Troubleshooting

| You see | Because | Do |
|---|---|---|
| `... is not a private network` or `... has N addresses; at most 1024` | `--cidr` names a public range or one larger than a /22 | use a private range of at most 1024 addresses |
| Few or no devices found | the system's neighbour table is filled by a poke of every address, which needs the permission to ping or to read it | run it with the permissions of a user that may ping and read the neighbour table |
| A fragile device misbehaves when scanned | it does not like the ports being tried | add `--skip <address>` (repeatable) or `--no-ports` |
| Studio never gets a message | the server cannot be reached or refuses the token (the problem is counted like any other: `unreachable`, `unauthorized`) | check `--server-url` and the token (the one of this node that Studio shows, or the shared ingest token) |

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-NETWORK" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
ARMOR-NETWORK/
├── src/armor_network/
│   ├── ipnet.py oui.py                      what may be probed; the makers
│   ├── system_io.py sim_io.py               the real network; a scripted one
│   ├── neighbors.py parsers.py dnswire.py   what the system and devices say
│   ├── services.py                          ports and guesses
│   ├── inventory.py internet.py             devices and events; the outage machine
│   ├── agent.py publisher.py mqtt_out.py    what to look at; how it reports
│   ├── orders.py seal.py                    orders from Studio; sealed logins
│   ├── cli.py __main__.py                   scan, watch and demo
│   └── data/                                oui.tsv.gz, the IEEE register
├── tests/                                   187 tests in 9 modules
├── docs/                                    DESIGN, SAFETY, USAGE, MESSAGES
├── tools/                                   fetch_oui.py refreshes the register of makers; the shared CI checks and launcher
├── images/                                  banner, icon and the pictures of the README
├── .github/                                 CI workflow, dashboard notice, issue and pull-request templates
├── armor.project.json                       manifest: version, role, maturity
├── pyproject.toml                           package metadata, entry points
├── CHANGELOG.md                             what changed in each version
├── run.sh run.bat                           start, shared workflow
├── build.sh build.bat                       build and test, shared workflow
├── build-test.sh build-test.bat             build, test and package
├── test.sh test.bat                         only the tests, never the version
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roadmap & Known limits

**Known limits today**

* It has not watched a whole house for weeks.
* It only asks the router and never configures it; what a device is (kind, system, maker) is a guess.
* It does not capture packets, so it cannot see who talks to whom; traffic per device and intrusion detection in the strict sense need the router's counters or a mirror port.
* No independent security review.

**Next**

* The router's own counters (traffic per device), packet capture and weeks on a real network.
* Controlling something (blocking a device, closing a port, changing the router) is not planned without a documented risk review.

## 🌍 Languages

README and texts exist in English, Spanish, French, Italian, German, Chinese, Japanese and European Portuguese.

## 🔗 Related Projects

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) is a perimeter-security system made of independent repositories. Each one has its own version, its own tests and its own README; this is the family:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Message contracts, validators, conformance vectors and generated types
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Field-node firmware for ESP32-S3 with three radars and its own web panel
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Solar inverter and battery protocols and the messages of a gateway node
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Electrical node: meters, the message of the network's readings and the rules for switching
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Alarm node and panel: zones, arming, delays, siren and PIN, with the server or without it
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Touch panel: the state of the system on a wall screen, arming and acknowledging, and the home of the voice assistant
* **ARMOR-NETWORK** (this repository) - The local network: its devices, the internet and what changes
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Central coordinator: telemetry, alarms, devices, solar readings and cameras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web console: cameras, radar, alarms, solar energy and the 2D/3D site designer
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Android operator client with a live 2D/3D radar
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone operator client
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Visual inference policy that explains its decisions and never actuates
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Camera zones, masks and detection rules for the Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Offline voice intents with a confirmation that cannot be forged
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Enclosures, electronics and the bench acceptance matrix
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Deployment, the CM5 test bench, backup and TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Offline telemetry simulator with repeatable faults
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Detects, installs and updates the ecosystem's own repositories
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, security baseline and the capability matrix

## 📚 Documentation

* [Design](docs/DESIGN.md): how the node looks, remembers and decides
* [Safety](docs/SAFETY.md): what it may touch and what it never does
* [Usage](docs/USAGE.md): the commands, the flags and the systemd unit
* [Messages](docs/MESSAGES.md): the message of the node and its orders
* [Capability matrix: what is proven and what is not](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Project catalogue: versions and how the repositories depend on each other](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Changelog of this repository](CHANGELOG.md)

## 🤝 Contributing & Community

* Before a pull request run `python -I tools/armor_ci_validate.py` and the tests: both must pass. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md).
* The README exists in eight languages and is generated from the sources in ARMOR-DOCS: a change to the text is made there.
* A change to a message between components starts in ARMOR-COMMON.
* Do not describe as working on a board what has only been built.
* Report a vulnerability privately: [SECURITY.md](SECURITY.md). Questions, ideas and reports: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - see [LICENSE](LICENSE).
