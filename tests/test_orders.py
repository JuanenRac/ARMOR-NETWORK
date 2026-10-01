"""Tests of the public address and of the manual orders: what is kept of a public service's answer, which orders and addresses are refused, and the whole agent
doing each order against the scripted network, with every message checked by ARMOR-COMMON's contract. Nothing here touches a network."""
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
COMMON = ROOT.parent / "ARMOR-COMMON" / "src"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from armor_network import orders  # noqa: E402
from armor_network.agent import Agent, Config  # noqa: E402
from armor_network.publisher import deliver  # noqa: E402
from armor_network.sim_io import SimIO  # noqa: E402

try:
    from armor_common import validate_network_message
except ImportError:                                  # the contract is optional for this project's own tests
    validate_network_message = None


class Clock:
    now = 0

    def __call__(self):
        return self.now


def run_agent(*order_list: orders.Order, config: Config | None = None):
    clock = Clock()
    io = SimIO(clock)
    agent = Agent(io, config or Config(scan_every_s=10, publish_every_s=10, internet_every_s=5))
    clock.now = io._t0
    agent.step()
    clock.now = io._t0 + 10_000
    agent.submit(list(order_list))
    message = agent.step()
    assert message is not None
    if validate_network_message is not None:
        validate_network_message(f"armor/network/{message['node_id']}/state", message)
    return agent, io, clock, message


class PublicInfoTests(unittest.TestCase):
    def test_what_a_service_answers_is_reduced_to_what_the_contract_holds(self):
        info = orders.clean_public_info({"ip": " 203.0.113.9 ", "city": "Madrid", "org": "AS64496 EXAMPLE TELECOM", "readme": "x", "hostname": "h" * 500, "region": 3})
        self.assertEqual(info["ip"], "203.0.113.9")
        self.assertEqual(info["city"], "Madrid")
        self.assertEqual(len(info["hostname"]), 128)
        self.assertNotIn("readme", info)
        self.assertNotIn("region", info)
        for bad in (None, [], {}, {"ip": "not an address"}, {"ip": "999.1.1.1"}, {"ip": 7}):
            with self.subTest(bad):
                self.assertIsNone(orders.clean_public_info(bad))
        self.assertEqual(orders.clean_public_info({"ip": "2a02:9000::1"})["ip"], "2a02:9000::1")

    def test_only_an_https_address_is_asked(self):
        self.assertEqual(orders.check_public_url("https://ipinfo.io/json"), "https://ipinfo.io/json")
        for bad in ("http://ipinfo.io/json", "ipinfo.io", "https://user:pw@x.io/a", "https://x.io/a b", "file:///etc/passwd", ""):
            with self.subTest(bad), self.assertRaises(ValueError):
                orders.check_public_url(bad)

    def test_the_address_is_noticed_to_change_and_remembered(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "public.json"
            tracker = orders.PublicTracker(path)
            self.assertIsNone(tracker.block())
            tracker.update({"ip": "1.2.3.4"}, 1000)
            self.assertEqual(tracker.block(), {"ip": "1.2.3.4", "checked_ms": 1000})        # first time: nothing changed
            tracker.update({"ip": "1.2.3.4"}, 2000)
            self.assertNotIn("changed_ms", tracker.block())
            tracker.update({"ip": "198.51.100.8"}, 3000)
            self.assertEqual(tracker.block(), {"ip": "198.51.100.8", "checked_ms": 3000, "changed_ms": 3000})
            tracker.update(None, 4000)                                                       # a failed lookup keeps what was known
            self.assertEqual(tracker.block()["ip"], "198.51.100.8")
            again = orders.PublicTracker(path)
            self.assertEqual(again.block()["changed_ms"], 3000)

    def test_the_agent_tells_the_public_address_unless_told_not_to(self):
        _agent, _io, _clock, message = run_agent()
        self.assertEqual(message["public"]["ip"], "203.0.113.9")
        self.assertEqual(message["public"]["country"], "ES")
        _agent, _io, _clock, quiet = run_agent(config=Config(scan_every_s=10, publish_every_s=10, public_info=False))
        self.assertNotIn("public", quiet)


class OrderTests(unittest.TestCase):
    def test_only_well_formed_orders_are_taken_and_at_most_four(self):
        body = {"commands": [{"id": "c01", "type": "ping", "ip": "192.168.0.50", "device_id": "aa:bb:cc:00:00:01"}, {"id": "Bad Id", "type": "ping"},
                             {"id": "c03", "type": "http", "ip": "192.168.0.50", "port": 70000}, {"id": "c04", "type": "wake", "mac": "AA:BB:CC:00:00:01"},
                             {"id": "c05", "type": "scan_now"}, {"id": "c06", "type": "scan_now"}]}
        taken = orders.parse_orders(body)
        self.assertEqual([order.id for order in taken], ["c01", "c03", "c04"], "only the first four are looked at, and of those the well-formed ones are kept")
        self.assertIsNone(taken[1].port)
        self.assertEqual(taken[2].mac, "aa:bb:cc:00:00:01")
        self.assertEqual(orders.parse_orders({"commands": [{"id": "c02", "type": "reboot"}, "text", {"id": "c07", "type": "ping", "port": True}]})[0].port, None)
        for nothing in (None, [], {}, {"commands": "ping"}, {"commands": None}):
            self.assertEqual(orders.parse_orders(nothing), [])

    def test_the_wake_up_packet_is_the_standard_one(self):
        packet = orders.magic_packet("aa:bb:cc:00:00:01")
        self.assertEqual(len(packet), 102)
        self.assertEqual(packet[:6], b"\xff" * 6)
        self.assertEqual(packet[6:12], bytes.fromhex("aabbcc000001"))
        with self.assertRaises(ValueError):
            orders.magic_packet("aa:bb")

    def test_an_order_may_only_be_about_a_private_address_of_the_watched_network(self):
        import ipaddress
        network = ipaddress.ip_network("192.168.0.0/24")
        self.assertTrue(orders.target_allowed("192.168.0.50", network, set(), "192.168.0.10"))
        for ip in ("8.8.8.8", "192.168.1.5", "192.168.0.10", "192.168.0.99", "10.0.0.1", "not an address", None, ""):
            with self.subTest(ip):
                self.assertFalse(orders.target_allowed(ip, network, {"192.168.0.99"}, "192.168.0.10"))

    def test_a_ping_a_traceroute_the_ports_and_the_page_of_a_device(self):
        _agent, io, _clock, _first = run_agent()
        device = next(d for d in io.devices if d.ports and d.hostname)
        base = dict(ip=device.ip, device_id=device.mac)
        _agent, _io, _clock, message = run_agent(orders.Order("o1", "ping", **base), orders.Order("o2", "traceroute", **base), orders.Order("o3", "ports", **base),
                                                 orders.Order("o4", "http", port=next(iter(device.ports)), **base))
        results = {r["id"]: r for r in message["results"]}
        self.assertTrue(results["o1"]["ok"])
        self.assertGreater(results["o1"]["latency_ms"], 0)
        self.assertIn(device.ip, results["o2"]["output"])
        self.assertTrue(results["o3"]["ok"])
        self.assertEqual({p["port"] for p in results["o3"]["ports"]}, set(device.ports))
        self.assertTrue(results["o4"]["ok"])
        self.assertIn("HTTP 200", results["o4"]["output"])
        self.assertTrue(all(r["device_id"] == device.mac for r in results.values()))

    def test_an_order_about_something_off_the_network_is_refused_and_told(self):
        _agent, _io, _clock, message = run_agent(orders.Order("o1", "ping", ip="8.8.8.8"), orders.Order("o2", "traceroute", ip="192.168.7.7"), orders.Order("o3", "wake", mac=None))
        results = {r["id"]: r for r in message["results"]}
        for identifier in ("o1", "o2"):
            self.assertFalse(results[identifier]["ok"])
            self.assertIn("not on the network", results[identifier]["output"])
        self.assertFalse(results["o3"]["ok"])
        self.assertIn("no MAC", results["o3"]["output"])

    def test_a_wake_up_goes_to_the_broadcast_of_the_network_and_nowhere_else(self):
        _agent, io, _clock, message = run_agent(orders.Order("w1", "wake", mac="aa:bb:cc:00:00:01", ip="192.168.0.50"))
        self.assertEqual(io.woken, [("aa:bb:cc:00:00:01", "192.168.0.255")])
        self.assertTrue(message["results"][0]["ok"])
        _agent, io, _clock, refused = run_agent(orders.Order("w2", "wake", mac="aa:bb:cc:00:00:01", ip="8.8.8.8"))
        self.assertEqual(io.woken, [])
        self.assertFalse(refused["results"][0]["ok"])

    def test_a_sweep_now_does_the_sweep_at_once_and_a_result_goes_out_for_two_minutes_only(self):
        clock = Clock()
        io = SimIO(clock)
        agent = Agent(io, Config(scan_every_s=600, publish_every_s=30, internet_every_s=5))
        clock.now = io._t0
        first = agent.step()
        clock.now = io._t0 + 10_000
        self.assertIsNone(agent.step(), "nothing is due: the next sweep is ten minutes away")
        agent.submit([orders.Order("s1", "scan_now")])
        message = agent.step()
        self.assertEqual(message["scan"]["last_ms"], io._t0 + 10_000, "the sweep was done at once")
        self.assertEqual(message["results"][0]["id"], "s1")
        clock.now = io._t0 + 45_000
        again = agent.step()
        self.assertEqual(again["results"][0]["id"], "s1", "it goes out again, in case the first was lost")
        clock.now = io._t0 + 10_000 + 130_000
        late = agent.step()
        self.assertNotIn("results", late)
        self.assertIsNotNone(first)

    def test_a_result_is_short_and_there_are_at_most_sixteen(self):
        class Loud(SimIO):
            def traceroute(self, ip):
                return "x" * 9000
        clock = Clock()
        io = Loud(clock)
        agent = Agent(io, Config(scan_every_s=10, publish_every_s=10))
        clock.now = io._t0
        agent.step()
        for batch in range(6):
            clock.now = io._t0 + 10_000 * (batch + 1)
            agent.submit([orders.Order(f"t{batch}{i}", "traceroute", ip="192.168.0.50") for i in range(4)])
            message = agent.step()
        self.assertEqual(len(message["results"]), 16)
        self.assertTrue(all(len(r["output"]) <= 2000 for r in message["results"]))
        if validate_network_message is not None:
            validate_network_message(f"armor/network/{message['node_id']}/state", message)


class AnswerHandler(BaseHTTPRequestHandler):
    reply: bytes = b""

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(202)
        self.end_headers()
        self.wfile.write(AnswerHandler.reply)

    def log_message(self, *args):
        pass


class DeliveryTests(unittest.TestCase):
    def test_the_orders_come_in_the_answer_and_an_older_server_gives_none(self):
        server = HTTPServer(("127.0.0.1", 0), AnswerHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            AnswerHandler.reply = json.dumps({"accepted": True, "commands": [{"id": "c9", "type": "ping", "ip": "192.168.0.50", "device_id": "aa:bb:cc:00:00:01"}]}).encode()
            self.assertEqual([(o.id, o.type, o.ip) for o in deliver(base, "tok", {"kind": "network"})], [("c9", "ping", "192.168.0.50")])
            AnswerHandler.reply = b'{"accepted":true}'
            self.assertEqual(deliver(base, "tok", {}), [])
            AnswerHandler.reply = b"not json"
            self.assertEqual(deliver(base, "tok", {}), [])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
