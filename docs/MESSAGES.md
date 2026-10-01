# The message of a network node (contract version 0)

`armor/network/{node_id}/state`, one message per node every ten seconds or when something happened; JSON, no retained flag; or `POST /api/v1/network/state` with the ingest token. The schema, the topic rule and the conformance vectors are in ARMOR-COMMON (`network.schema.json`, `conformance/network.json`, 64 vectors); the server takes it, keeps the latest state of every node, a history of the internet and of the traffic, the list of outages, and raises the alarms.

```json
{"kind":"network","node_id":"network-1","timestamp_ms":1790000060000,
 "interface":{"name":"Ethernet","ip":"192.168.0.10","cidr":"192.168.0.0/24","gateway":"192.168.0.1","rx_bps":1200000,"tx_bps":340000},
 "internet":{"state":"up","since_ms":1789990000000,"gateway_ok":true,"latency_ms":12.5,"loss_percent":0.0,
             "probes":[{"target":"1.1.1.1","kind":"dns","ok":true,"latency_ms":13.8}],
             "last_outage":{"started_ms":1789900000000,"ended_ms":1789900300000,"duration_s":300},"outages_24h":1,"downtime_24h_s":300},
 "devices":[{"id":"14:2e:5e:86:d9:62","ip":"192.168.0.1","mac":"14:2e:5e:86:d9:62","vendor":"Sercomm Corporation.","hostname":"router","kind":"router","os":"network equipment",
             "online":true,"first_seen_ms":1790000000000,"last_seen_ms":1790000060000,"latency_ms":1.4,
             "ports":[{"port":80,"proto":"tcp","service":"http","banner":"Router login"}],"services":["_http._tcp"]}],
 "events":[{"id":"e1","kind":"new_device","at_ms":1790000030000,"device_id":"96:b3:ed:0b:1c:18","detail":"192.168.0.12 (randomised address)"}],
 "scan":{"last_ms":1790000050000,"hosts":254,"duration_ms":9000}}
```

* **`internet.state`**: `up`, `degraded`, `down` (the router answers and nothing beyond it does: the provider's side), `lan_down` (the router does not answer either: this side) or `unknown` (just started).
* **A device** is its MAC in lowercase with colons, or `ip-<address with dashes>` until the MAC is known; a device with a MAC has it as its id. `randomized_mac` says the MAC is locally administered (a phone that changes it on purpose): it is not an identity, and it has no maker. `kind`, `os` and `vendor` are guesses.
* **Events** keep their id, oldest first, at most 64, so a reader that sees the same event twice counts it once. `new_device`, `device_online`, `device_offline`, `ip_changed`, `arp_conflict`, `port_opened` and `port_closed` are about a device (`device_id` required, `port` on the port events); `internet_down`, `internet_up`, `gateway_down` and `gateway_up` are not (no `device_id`, no `port`), and only the two `_up` events say how long it was down (`outage_s`).
* Up to 512 devices, 64 ports each, 16 announced services each, 8 probes. A field that is not in the schema is refused; no nulls: what is not known is left out.
* **`public`** (optional): the public address of the connection and what the service says of it (`city`, `region`, `country`, `org` - the provider and its autonomous system - `timezone`), `checked_ms`, and `changed_ms` when the address was seen to change.
* **`results`** (optional, at most 16): what the node did with the manual orders the server handed it in the answer to its previous message (`scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`), each with the `id` of its order, `ok`, `finished_ms` and, as it applies, `device_id`, `output`, `ports` and `latency_ms`. A result goes out in every message for two minutes, so one lost on the way is not lost.
* The message carries findings and results, never a command: the orders come the other way, in the answer to `POST /api/v1/network/state` (`{"commands": [...]}`, at most four, each handed out once).
