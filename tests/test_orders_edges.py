"""The edges of the manual orders: the public-address service, the wake-up packet, the look at a device's front page (against a stand-in on the loopback), the redirects a device may not
make, and the file where the certificates seen are kept. Nothing here reaches another machine."""
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import orders  # noqa: E402


class Page(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, dict, bytes]] = {}

    def log_message(self, *args):
        pass

    def do_GET(self):  # noqa: N802
        status, headers, body = Page.routes.get(self.path, (404, {}, b""))
        self.send_response_only(status)   # without the default Server and Date headers: the test says which ones the device sends
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Stand:
    def __init__(self):
        Page.routes = {}
        self.server = HTTPServer(("127.0.0.1", 0), Page)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self, size=-1):
        return self._body if size < 0 else self._body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class PublicServiceTests(unittest.TestCase):
    def test_a_good_answer_is_cleaned_and_asked_with_the_given_address_only(self):
        body = json.dumps({"ip": " 203.0.113.9 ", "city": "Town", "org": "x" * 500, "extra": "ignored", "hostname": ""}).encode()
        with mock.patch.object(orders, "urlopen", return_value=FakeResponse(body)) as opened:
            info = orders.fetch_public_info("https://ipinfo.example/json", timeout=1)
        self.assertEqual(info["ip"], "203.0.113.9")
        self.assertEqual(info["city"], "Town")
        self.assertEqual(len(info["org"]), 128)
        self.assertNotIn("extra", info)
        self.assertNotIn("hostname", info)
        self.assertEqual(opened.call_args.args[0].full_url, "https://ipinfo.example/json")

    def test_every_way_it_can_fail_is_none_and_never_an_exception(self):
        for effect in (OSError("down"), URLError("no route"), ValueError("bad")):
            with mock.patch.object(orders, "urlopen", side_effect=effect):
                self.assertIsNone(orders.fetch_public_info("https://ipinfo.example/json"))
        for body in (b"not json", b"[]", b'{"ip": "nope"}', b'{"ip": 5}', b"", b'{"city": "no ip"}'):
            with mock.patch.object(orders, "urlopen", return_value=FakeResponse(body)):
                self.assertIsNone(orders.fetch_public_info("https://ipinfo.example/json"), body)

    def test_an_address_that_is_not_https_is_not_even_asked(self):
        with mock.patch.object(orders, "urlopen") as opened:
            for url in ("http://ipinfo.example/json", "ftp://x/y", "https://", "https://user:pass@host/x", "file:///etc/passwd", "", "https://host/a b"):
                self.assertIsNone(orders.fetch_public_info(url), url)
        opened.assert_not_called()

    def test_an_ipv6_address_is_accepted_as_an_address(self):
        self.assertEqual(orders.clean_public_info({"ip": "2001:db8::1"}), {"ip": "2001:db8::1"})


class TrackerFileTests(unittest.TestCase):
    def test_a_damaged_file_is_forgotten_not_fatal(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "public.json"
            for text in ("{broken", "[]", '{"info": 5}', '{"info": {"ip": "x"}}', ""):
                path.write_text(text, encoding="utf-8")
                tracker = orders.PublicTracker(path)
                self.assertIsNone(tracker.info, text)
                self.assertIsNone(tracker.block())

    def test_a_folder_that_cannot_be_written_does_not_stop_the_watch(self):
        with tempfile.TemporaryDirectory() as folder:
            blocker = Path(folder) / "file"
            blocker.write_text("x", encoding="utf-8")
            tracker = orders.PublicTracker(blocker / "inside" / "public.json")      # its parent is a file
            tracker.update({"ip": "203.0.113.9"}, 1000)
            self.assertEqual(tracker.block(), {"ip": "203.0.113.9", "checked_ms": 1000})

    def test_a_failed_check_keeps_the_last_answer_and_only_moves_the_time(self):
        tracker = orders.PublicTracker()
        tracker.update({"ip": "203.0.113.9"}, 1000)
        tracker.update(None, 2000)
        self.assertEqual(tracker.block(), {"ip": "203.0.113.9", "checked_ms": 2000})
        tracker.update({"ip": "203.0.113.10"}, 3000)
        self.assertEqual(tracker.block()["changed_ms"], 3000)


class WakePacketTests(unittest.TestCase):
    def test_the_packet_is_six_ff_and_the_mac_sixteen_times(self):
        packet = orders.magic_packet("aa:bb:cc:00:11:22")
        self.assertEqual(len(packet), 102)
        self.assertEqual(packet[:6], b"\xff" * 6)
        self.assertEqual(packet[6:12], bytes.fromhex("aabbcc001122"))
        self.assertEqual(packet[6:], bytes.fromhex("aabbcc001122") * 16)

    def test_something_that_is_not_a_mac_makes_no_packet(self):
        for bad in ("aa:bb:cc", "aa:bb:cc:dd:ee:ff:00", "zz:zz:zz:zz:zz:zz", ""):
            with self.assertRaises(ValueError, msg=bad):
                orders.magic_packet(bad)

    def test_it_is_broadcast_once_to_the_discard_port_of_the_given_address(self):
        with mock.patch.object(orders.socket, "socket") as make:
            sock = make.return_value.__enter__.return_value
            orders.send_magic_packet("aa:bb:cc:00:11:22", "192.168.0.255")
        sock.sendto.assert_called_once()
        data, address = sock.sendto.call_args.args
        self.assertEqual((len(data), address), (102, ("192.168.0.255", 9)))
        sock.setsockopt.assert_called_once_with(orders.socket.SOL_SOCKET, orders.socket.SO_BROADCAST, 1)

    def test_a_bad_mac_sends_nothing(self):
        with mock.patch.object(orders.socket, "socket") as make:
            with self.assertRaises(ValueError):
                orders.send_magic_packet("nonsense", "192.168.0.255")
        make.assert_not_called()


class FrontPageTests(unittest.TestCase):
    def setUp(self):
        self.stand = Stand()
        self.addCleanup(self.stand.close)

    def test_the_status_the_server_header_and_the_title_are_reported(self):
        Page.routes["/"] = (200, {"Server": "lighttpd/1.4"}, b"<html><head><title>\n  My   Router \n</title></head></html>")
        result = orders.http_look("127.0.0.1", self.stand.port)
        self.assertTrue(result["ok"])
        self.assertIn(f"http://127.0.0.1:{self.stand.port}/ -> HTTP 200", result["output"])
        self.assertIn("server: lighttpd/1.4", result["output"])
        self.assertIn("title: My Router", result["output"])

    def test_a_page_without_title_or_server_says_only_the_status(self):
        Page.routes["/"] = (200, {}, b"<html>nothing</html>")
        self.assertEqual(orders.http_look("127.0.0.1", self.stand.port)["output"].count("\n"), 0)

    def test_a_long_title_is_cut_and_only_the_start_of_a_huge_page_is_read(self):
        Page.routes["/"] = (200, {}, b"<title>" + b"t" * 500 + b"</title>" + b"x" * 1_000_000)
        output = orders.http_look("127.0.0.1", self.stand.port)["output"]
        self.assertLessEqual(len(output.split("title: ")[1]), 120)

    def test_a_device_that_does_not_answer_is_said_plainly(self):
        self.stand.close()
        result = orders.http_look("127.0.0.1", self.stand.port, timeout=0.5)
        self.assertFalse(result["ok"])
        self.assertTrue(result["output"].startswith("no answer"))
        self.assertLessEqual(len(result["output"]), 200)

    def test_a_redirect_to_a_public_host_is_not_followed(self):
        Page.routes["/"] = (302, {"Location": "http://203.0.113.50/login"}, b"")
        result = orders.http_look("127.0.0.1", self.stand.port)
        self.assertFalse(result["ok"])
        self.assertIn("not on the local network", result["output"])

    def test_a_redirect_back_to_the_loopback_is_refused_too(self):
        Page.routes["/"] = (302, {"Location": f"http://127.0.0.1:{self.stand.port}/next"}, b"")
        Page.routes["/next"] = (200, {}, b"<title>Arrived</title>")
        # 127.0.0.1 is not one of the private ranges of this program, so even a redirect back to the same machine is refused: the rule has no exceptions
        self.assertFalse(orders.http_look("127.0.0.1", self.stand.port)["ok"])

    def test_the_redirect_handler_decides_by_the_private_ranges(self):
        handler = orders._PrivateRedirects()
        request = mock.Mock(full_url="http://192.168.0.5/", get_method=lambda: "GET", headers={}, origin_req_host="192.168.0.5", unverifiable=False, data=None)
        for target in ("http://8.8.8.8/x", "http://example.org/", "http:///nowhere", "http://172.32.0.1/"):
            with self.assertRaises(URLError, msg=target):
                handler.redirect_request(request, mock.Mock(), 302, "Found", {}, target)


class PinFileTests(unittest.TestCase):
    def test_the_first_certificate_is_kept_the_same_one_is_the_same_and_another_one_is_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pins" / "https-pins.json"
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "a" * 64, path), "new")
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "a" * 64, path), "same")
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "b" * 64, path), "changed")
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "a" * 64, path), "same")             # a changed certificate did not replace the kept one
            self.assertEqual(orders.check_pin("192.168.0.9", 8443, "b" * 64, path), "new")            # the port is part of the identity
            self.assertEqual(orders.check_pin("192.168.0.10", 443, "b" * 64, path), "new")
            self.assertEqual(sorted(json.loads(path.read_text(encoding="utf-8"))), ["192.168.0.10:443", "192.168.0.9:443", "192.168.0.9:8443"])

    def test_the_file_is_private_and_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pins.json"
            orders.check_pin("192.168.0.9", 443, "a" * 64, path)
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual([item.name for item in Path(folder).iterdir()], ["pins.json"])

    def test_a_damaged_or_foreign_file_starts_again_from_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pins.json"
            for text in ("{broken", "[1, 2]", '"text"', ""):
                path.write_text(text, encoding="utf-8")
                self.assertEqual(orders.check_pin("192.168.0.9", 443, "a" * 64, path), "new", text)

    def test_a_file_that_cannot_be_written_still_gives_an_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            blocker = Path(folder) / "file"
            blocker.write_text("x", encoding="utf-8")
            self.assertEqual(orders.check_pin("192.168.0.9", 443, "a" * 64, blocker / "pins.json"), "new")

    def test_the_default_place_comes_from_the_environment(self):
        with mock.patch.dict(os.environ, {"ARMOR_NETWORK_PINS": "/somewhere/pins.json"}):
            self.assertEqual(orders.pin_file(), Path("/somewhere/pins.json"))
        with mock.patch.dict(os.environ, {"ARMOR_NETWORK_PINS": ""}):
            self.assertEqual(orders.pin_file().name, "https-pins.json")

    def test_the_fingerprint_is_none_when_nothing_answers_and_a_hash_of_the_certificate_otherwise(self):
        with mock.patch.object(orders.socket, "create_connection", side_effect=OSError("refused")):
            self.assertIsNone(orders.certificate_fingerprint("192.168.0.9", 443, 0.2))
        tls = mock.MagicMock()
        tls.__enter__.return_value.getpeercert.return_value = b"der-bytes"
        context = mock.Mock()
        context.wrap_socket.return_value = tls
        with mock.patch.object(orders.socket, "create_connection"), mock.patch.object(orders.ssl, "create_default_context", return_value=context):
            import hashlib
            self.assertEqual(orders.certificate_fingerprint("192.168.0.9", 443, 0.2), hashlib.sha256(b"der-bytes").hexdigest())
            tls.__enter__.return_value.getpeercert.return_value = b""
            self.assertIsNone(orders.certificate_fingerprint("192.168.0.9", 443, 0.2))


class CheckPublicUrlTests(unittest.TestCase):
    def test_the_accepted_and_refused_addresses(self):
        for good in ("https://ipinfo.io/json", "https://example.org:8443/a/b.json", "https://a.b-c.d/x%20y"):
            self.assertEqual(orders.check_public_url(good), good)
        for bad in ("http://ipinfo.io/json", "https://ipinfo.io/json?token=secret", "https://ipinfo.io/json#x", "https://u@ipinfo.io/", "https://ipinfo.io:99999999/", "//ipinfo.io/", "https:/ipinfo.io"):
            with self.assertRaises(ValueError, msg=bad):
                orders.check_public_url(bad)


if __name__ == "__main__":
    unittest.main()
