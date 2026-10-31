"""Tests of the public address and of the manual orders: what is kept of a public service's answer, which orders and addresses are refused, and the whole agent
doing each order against the scripted network, with every message checked by ARMOR-COMMON's contract. Nothing here touches a network."""
import json
import io
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock
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


class DnsNameTests(unittest.TestCase):
    def test_only_a_host_name_is_taken(self):
        self.assertEqual(orders.check_dns_name("Home.Example.NET"), "home.example.net")
        for bad in ("", "-bad.example.net", "a b.example.net", "http://home.example.net", "home..example.net", "x" * 64 + ".net", "a;rm.net"):
            with self.subTest(bad), self.assertRaises(ValueError):
                orders.check_dns_name(bad)

    def test_a_name_that_does_not_resolve_gives_nothing_and_never_raises(self):
        with mock.patch("socket.getaddrinfo", side_effect=OSError("no such name")):
            self.assertEqual(orders.resolve_dns_name("home.example.net"), [])
        with mock.patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("203.0.113.9", 0)), (2, 1, 6, "", ("203.0.113.9", 0)), (10, 1, 6, "", ("2001:db8::1", 0, 0, 0))]):
            self.assertEqual(orders.resolve_dns_name("home.example.net"), ["2001:db8::1", "203.0.113.9"])

    def test_the_message_says_whether_the_name_follows_the_public_address(self):
        _agent, io, _clock, message = run_agent(config=Config(scan_every_s=10, publish_every_s=10, internet_every_s=5, dns_name="home.example.net"))
        self.assertEqual(message["public"]["dns"], {"name": "home.example.net", "addresses": ["203.0.113.9"], "matches": True})
        clock = Clock()
        sim = SimIO(clock)
        sim.dns_answer = ["198.51.100.4"]
        agent = Agent(sim, Config(scan_every_s=10, publish_every_s=10, internet_every_s=5, dns_name="home.example.net"))
        clock.now = sim._t0
        message = agent.step()
        self.assertEqual(message["public"]["dns"], {"name": "home.example.net", "addresses": ["198.51.100.4"], "matches": False})
        if validate_network_message is not None:
            validate_network_message(f"armor/network/{message['node_id']}/state", message)
        sim.dns_answer = []
        clock.now = sim._t0 + 700_000
        message = agent.step()
        self.assertEqual(message["public"]["dns"]["addresses"], [])
        self.assertFalse(message["public"]["dns"]["matches"])

    def test_without_a_name_the_message_has_no_dns(self):
        _agent, _io, _clock, message = run_agent()
        self.assertNotIn("dns", message["public"])


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


class InspectTests(unittest.TestCase):
    """Looking at a device's web administration with the login the person gave: asked once, never guessed, never echoed."""

    def _server(self, user="admin", password="s3cret"):
        import base64
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        expected = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        patch = mock.patch.dict(os.environ, {"ARMOR_NETWORK_ALLOW_BASIC_HTTP": "1"})   # these tests talk Basic to a local server over plain HTTP
        patch.start()
        self.addCleanup(patch.stop)

        class Handler(BaseHTTPRequestHandler):
            server_version = "tiny-httpd"
            sys_version = ""

            def do_GET(self):  # noqa: N802
                if self.headers.get("Authorization") != expected:
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="Router"')
                    self.end_headers()
                    return
                body = b"<html><head><title>Home Router</title></head><body>Model: HR-5000 <br> Firmware Version: 2.1.4 <br> password is s3cret</body></html>"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):  # noqa: D401
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def test_the_login_the_person_gave_is_tried_once_and_what_the_page_says_is_read(self):
        port = self._server()
        found = orders.inspect_web("127.0.0.1", port, "admin", "s3cret")
        self.assertTrue(found["ok"])
        for line in ("HTTP 200", "login: accepted (Basic)", 'realm: Router', "server: tiny-httpd", "title: Home Router", "model: HR-5000", "firmware: 2.1.4"):
            self.assertIn(line, found["output"])
        self.assertNotIn("s3cret", found["output"], "the login is never echoed back, not even by the device's own page")

    def test_a_wrong_login_is_refused_and_no_login_says_that_one_is_required(self):
        port = self._server()
        refused = orders.inspect_web("127.0.0.1", port, "admin", "wrong")
        self.assertFalse(refused["ok"])
        self.assertIn("login: refused", refused["output"])
        none = orders.inspect_web("127.0.0.1", port, None, None)
        self.assertIn("required (Basic), no login was given", none["output"])

    def test_a_factory_login_that_works_is_flagged(self):
        port = self._server("admin", "admin")
        found = orders.inspect_web("127.0.0.1", port, "admin", "admin")
        self.assertIn("factory login", found["output"])

    def test_a_login_is_not_sent_in_Basic_over_plain_http_unless_it_is_allowed(self):
        port = self._server()
        with mock.patch.dict(os.environ, {"ARMOR_NETWORK_ALLOW_BASIC_HTTP": "0"}):
            found = orders.inspect_web("127.0.0.1", port, "admin", "s3cret")
        self.assertFalse(found["ok"])
        self.assertIn("login: not sent", found["output"])
        self.assertNotIn("s3cret", found["output"])

    def test_the_certificate_seen_first_is_kept_and_another_one_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pins.json"
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "aa" * 32, path), "new")
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "aa" * 32, path), "same")
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "bb" * 32, path), "changed")
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "aa" * 32, path), "same", "a changed certificate is not kept")
            self.assertEqual(orders.check_pin("192.168.0.9", 8443, "bb" * 32, path), "new", "each address and port has its own")
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "cc" * 32, path), "new", "a damaged file is started again")

    def test_a_login_is_not_sent_to_an_https_device_whose_certificate_changed(self):
        from email.message import Message
        from urllib.error import HTTPError
        sent = []

        changed = []

        def fake_open(url, user, password, context, timeout, pin=None):
            if user is not None and changed:
                raise orders.PinChanged("bb" * 32)
            if user is None:
                headers = Message()
                headers["WWW-Authenticate"] = 'Digest realm="Cam"'
                raise HTTPError(url, 401, "Unauthorized", headers, io.BytesIO(b""))
            sent.append((url, user))

            class Page:
                status = 200
                headers = {"Server": "cam"}

                def read(self, n):
                    return b"<title>Cam</title>"

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False
            return Page()

        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"ARMOR_NETWORK_PINS": str(Path(folder) / "pins.json")}), mock.patch.object(orders, "_open", fake_open):
            first = orders.inspect_web("192.168.0.9", 443, "admin", "s3cret")
            self.assertIn("login: accepted", first["output"])
            changed.append(True)
            second = orders.inspect_web("192.168.0.9", 443, "admin", "s3cret")
            self.assertFalse(second["ok"])
            self.assertIn("login: not sent", second["output"])
            self.assertNotIn("s3cret", second["output"])
        self.assertEqual(len(sent), 1, "the login went only to the device whose certificate was first seen")

    def test_a_login_is_never_opened_over_plain_http_across_the_network(self):
        from armor_network import publisher
        self.assertTrue(publisher.login_may_travel("https://192.168.0.180:18080"))
        self.assertTrue(publisher.login_may_travel("http://127.0.0.1:18080"))
        self.assertFalse(publisher.login_may_travel("http://192.168.0.180:18080"))
        body = {"commands": [{"id": "a1", "type": "inspect", "ip": "192.168.0.9", "auth": {"user": "admin", "password": "x"}, "auth_sealed": "AAAA"}]}
        order = orders.parse_orders(body, "tok", allow_login=False)[0]
        self.assertTrue(order.login_withheld)
        self.assertIsNone(order.user)

    def test_a_wrong_mac_or_a_conflict_withholds_the_login(self):
        agent, io, clock, first = run_agent()
        calls = []
        io.inspect_web = lambda ip, port, user, password: calls.append((user, password)) or {"ok": True, "output": "looked"}
        io.arp_table = lambda: {"192.168.0.50": "aa:aa:aa:aa:aa:aa"}
        order = orders.Order("w1", "inspect", ip="192.168.0.50", mac="bb:bb:bb:bb:bb:bb", user="admin", password="p")
        agent.submit([order]); agent.step()
        self.assertEqual(calls[-1], (None, None))
        good = orders.Order("w2", "inspect", ip="192.168.0.50", mac="aa:aa:aa:aa:aa:aa", user="admin", password="p")
        agent.submit([good]); agent.step()
        self.assertEqual(calls[-1], ("admin", "p"))

    def test_a_route_without_a_gateway_and_the_lowest_metric(self):
        from armor_network import parsers
        self.assertEqual(parsers.parse_ip_route("default dev wwan0 scope link"), (None, "wwan0"))
        self.assertEqual(parsers.parse_ip_route("default via 10.0.0.1 dev eth0 metric 600" + chr(10) + "default via 192.168.0.1 dev wlan0 metric 100"), ("192.168.0.1", "wlan0"))

    def test_vendors_are_matched_by_whole_words(self):
        from armor_network.services import guess_kind
        self.assertEqual(guess_kind(vendor="zte corporation"), "network")
        self.assertNotEqual(guess_kind(vendor="aztech electronics"), "network")
        self.assertNotEqual(guess_kind(vendor="harris corporation"), "network")

    def test_an_order_that_was_already_done_is_not_done_twice(self):
        agent, io, clock, first = run_agent()
        order = orders.Order("dup1", "ping", ip="192.168.0.50") if hasattr(orders, "Order") else None
        if order is None:
            self.skipTest("the order type has another name")
        agent.submit([order]); agent.step()
        agent.submit([order])
        self.assertEqual(len(agent._orders), 0)

    def test_no_web_interface_is_said_plainly(self):
        found = orders.inspect_web("127.0.0.1", 9, "admin", "x", timeout=0.5)
        self.assertFalse(found["ok"])
        self.assertIn("no web interface answered", found["output"])

    def test_the_login_travels_only_in_an_inspect_order_and_stays_out_of_every_printout(self):
        parsed = orders.parse_orders({"commands": [
            {"id": "i1", "type": "inspect", "ip": "192.168.0.50", "auth": {"user": "admin", "password": "hunter2"}},
            {"id": "p1", "type": "ping", "ip": "192.168.0.50", "auth": {"user": "admin", "password": "hunter2"}},
            {"id": "i2", "type": "inspect", "ip": "192.168.0.51", "auth": {"user": "", "password": "x"}}]})
        self.assertEqual((parsed[0].user, parsed[0].password), ("admin", "hunter2"))
        self.assertEqual((parsed[1].user, parsed[1].password), (None, None))
        self.assertEqual((parsed[2].user, parsed[2].password), (None, None))
        self.assertNotIn("hunter2", repr(parsed[0]))
        self.assertNotIn("hunter2", str(parsed[0]))

    def test_the_agent_does_an_inspect_order_on_its_network_only(self):
        _agent, io, _clock, _first = run_agent()
        device = next(d for d in io.devices if d.ports and d.hostname)
        port = next(iter(device.ports))
        _agent, _io, _clock, message = run_agent(orders.Order("n1", "inspect", ip=device.ip, device_id=device.mac, port=port, user="admin", password="admin"),
                                                 orders.Order("n2", "inspect", ip="8.8.8.8", user="admin", password="admin"))
        results = {r["id"]: r for r in message["results"]}
        self.assertIn("login: accepted", results["n1"]["output"])
        self.assertNotIn("password", results["n1"]["output"].lower().replace("factory login", ""))
        self.assertFalse(results["n2"]["ok"])
        self.assertIn("not on the network", results["n2"]["output"])
