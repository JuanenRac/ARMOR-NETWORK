# Safety: what this program sends, and what it will not

A program that looks at a network is only welcome if what it sends is small, boring and on the owner's own network. This document says what ARMOR-NETWORK does about that, and where the rule is enforced.

## The rule that decides what may be probed

`ipnet.check_scan_range` is the one place. It refuses, for a scan, any network that is not entirely inside 10.0.0.0/8, 172.16.0.0/12 or 192.168.0.0/16, any range of more than 1,024 addresses (a /22) and any prefix longer than /30. Every function of `system_io.py` that talks to a device (`scan_ports`, `ping_many`, `resolve`, `poke`) refuses an address that is not private (`is_private_address`), whatever it was asked. The tests check that a public address gets no probe and no port scan, and that `armor-network scan --cidr 8.8.8.0/24` exits with a refusal.

The only traffic that leaves the private range is the internet check: a TCP connection to `1.1.1.1:443`, one DNS question to `1.1.1.1` and one to `8.8.8.8`, and one web request to `connectivitycheck.gstatic.com`.

## What is sent to a device, complete

An ICMP echo; a one-byte UDP datagram to port 9 (so the system resolves the address); a TCP connection to a list of ports (17, or 44), each closed as soon as what it says is read (at most a few hundred bytes; for a web port, a minimal `GET /`); the multicast questions of mDNS and SSDP and one request to the description a UPnP device publishes (a page of at most 16 kB, only from the address that announced it); a NetBIOS name request; a reverse DNS lookup. **Nothing else.** No password, no login, no exploit, no fuzzing, no attempt to change anything on a device.

## Being gentle

* Twelve connections at a time at most, to one device; at most four devices have their ports looked at in one turn, a new one at once and the others every quarter of an hour.
* `--skip ADDRESS` (repeatable) keeps a device out of every probe, for a piece of equipment that must not be poked.
* A name lookup that takes too long is left behind (`bounded`): the system's lookup ignores timeouts, and one of them took sixteen seconds for a phone that did not answer.
* The program is quiet on the network between turns: a sweep every minute, the internet every five seconds.

## What it keeps

The inventory (`inventory.json`) and the outages (`internet.json`) in `--data-dir`, written atomically; they hold MAC addresses, addresses and names of the devices of the house. They are as private as the network, and the server keeps its own copy of the names an administrator gives. The MAC of a device is not a secret (anyone on the network sees it), but it identifies devices, so keep the folder off shared places.

## What a finding is and is not

Everything the program reports is a finding about the network: the kind of a device, its system and its maker are guesses; an address or a MAC can be lied about by whoever owns the device (an `arp_conflict` is a reason to look, not a verdict); a device that does not appear may be asleep. The server raises alarms from these findings and says so.
