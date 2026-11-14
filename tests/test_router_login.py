"""The login to the router (TR-064 and OpenWrt), opt-in: what it asks, what it refuses, how the password is kept, and that it names the devices only when it was turned on.
Everything is tested against stand-ins (functions and a local web server); no real router has been asked. Nothing here touches the network.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later."""
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from armor_network import cli, config_file, router_login, system_io  # noqa: E402
from armor_network.agent import Agent, Config  # noqa: E402
from armor_network.router_login import RouterLogin  # noqa: E402
from armor_network.seal import open_sealed, seal_text  # noqa: E402
from armor_network.sim_io import SimIO  # noqa: E402

TOKEN = "k" * 64
SECRET = "correct horse"


# What the HTTP digest scheme of the routers asks for. The old 128-bit digest is part of that protocol (RFC 7616 keeps it as the default), so the stand-in has to
# speak it to check what the client sent; it is the only place of the tests that does, and the first-step value below is a fixed literal, so no password is hashed here.
STAND_IN_HA1 = "ddfc9b19e908a78667f595674ac84ba0"


def digest_hex(text):
    return hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()


def tr064_answer(entries):
    """A stand-in for the Hosts service: the number of entries and each entry by index."""
    def http(url, body, headers, user, password):
        text = body.decode()
        if (user, password) != ("fritz", SECRET):
            return 401, ""
        if "GetHostNumberOfEntries" in text:
            return 200, f"<NewHostNumberOfEntries>{len(entries)}</NewHostNumberOfEntries>"
        index = int(re.search(r"<NewIndex>(\d+)</NewIndex>", text).group(1))
        ip, mac, name = entries[index]
        return 200, f"<NewIPAddress>{ip}</NewIPAddress><NewMACAddress>{mac}</NewMACAddress><NewHostName>{name}</NewHostName>"
    return http


def ubus_answer(leases, session="a" * 32):
    def http(url, body, headers, user, password):
        call = json.loads(body)
        _, obj, method, params = call["params"]
        if (obj, method) == ("session", "login"):
            if params != {"username": "root", "password": SECRET}:
                return 200, json.dumps({"jsonrpc": "2.0", "id": 1, "result": [6]})
            return 200, json.dumps({"jsonrpc": "2.0", "id": 1, "result": [0, {"ubus_rpc_session": session}]})
        if (obj, method) == ("luci-rpc", "getDHCPLeases") and call["params"][0] == session:
            return 200, json.dumps({"jsonrpc": "2.0", "id": 2, "result": [0, {"dhcp_leases": leases}]})
        return 200, json.dumps({"result": [2]})
    return http


class Credential(unittest.TestCase):
    def test_a_sealed_password_opens_only_with_the_token_it_was_sealed_with(self):
        sealed = seal_text(TOKEN, SECRET)
        self.assertEqual(open_sealed(TOKEN, sealed), SECRET)
        self.assertIsNone(open_sealed("j" * 64, sealed))
        self.assertIsNone(open_sealed(TOKEN, sealed[:-4] + "AAAA"))
        self.assertNotIn(SECRET, sealed)
        self.assertNotEqual(seal_text(TOKEN, SECRET), sealed, "a fresh nonce each time")
        self.assertEqual(seal_text(TOKEN, "hello", nonce=bytes([7]) * 16), "BwcHBwcHBwcHBwcHBwcHB3DjzPUrsd3Gaw4Uk/BJhSrk1lLZbEo7RPBc5R3QOGEQdtGjYbg=")

    def test_the_default_is_not_to_keep_it_and_to_ask_each_time(self):
        self.assertEqual(config_file.FileSettings().router_credential, "ask")
        self.assertEqual(router_login.resolve_password("ask", "", "", {}, None)[0], None)
        self.assertEqual(router_login.resolve_password("ask", "", "", {router_login.ROUTER_LOGIN_ENV: SECRET}, None), (SECRET, ""))
        self.assertEqual(router_login.resolve_password("ask", "", "", {}, lambda: SECRET), (SECRET, ""))
        self.assertIsNone(router_login.resolve_password("ask", "", "", {}, lambda: "")[0])

    def test_a_sealed_one_needs_the_seal_and_the_token(self):
        sealed = seal_text(TOKEN, SECRET)
        self.assertEqual(router_login.resolve_password("sealed", sealed, TOKEN, {}, None), (SECRET, ""))
        for stored, token in (("", TOKEN), (sealed, ""), (sealed, "j" * 64)):
            password, why = router_login.resolve_password("sealed", stored, token, {}, None)
            self.assertIsNone(password)
            self.assertTrue(why)

    def test_the_password_is_never_in_the_text_of_the_login(self):
        login = RouterLogin("tr064", "http://192.168.0.1:49000", "fritz", SECRET)
        self.assertNotIn(SECRET, repr(login))
        self.assertIn("password=set", repr(login))


class Addresses(unittest.TestCase):
    def test_only_a_private_address_without_a_login_in_it(self):
        self.assertIsNone(router_login.check_url("http://192.168.0.1:49000", "tr064", False))
        self.assertIsNone(router_login.check_url("https://192.168.1.1", "openwrt", False))
        for url in ("http://8.8.8.8", "ftp://192.168.0.1", "http://user:pw@192.168.0.1", "http:///x", "192.168.0.1"):
            self.assertIsNotNone(router_login.check_url(url, "tr064", False), url)

    def test_the_openwrt_login_does_not_go_over_plain_http_unless_asked(self):
        self.assertIsNotNone(router_login.check_url("http://192.168.1.1", "openwrt", False))
        self.assertIsNone(router_login.check_url("http://192.168.1.1", "openwrt", True))
        self.assertEqual(router_login.default_url("tr064", "192.168.0.1"), "http://192.168.0.1:49000")
        self.assertEqual(router_login.default_url("openwrt", "192.168.1.1"), "https://192.168.1.1")


class Reading(unittest.TestCase):
    def test_tr064_names_the_devices(self):
        entries = [("192.168.0.30", "AA:BB:CC:00:00:30", "plug-kitchen"), ("192.168.0.31", "aa:bb:cc:00:00:31", "tv")]
        login = RouterLogin("tr064", "http://192.168.0.1:49000", "fritz", SECRET)
        self.assertEqual(router_login.read_names(login, tr064_answer(entries)), {"192.168.0.30": "plug-kitchen", "192.168.0.31": "tv"})

    def test_a_wrong_password_a_silent_router_and_garbage_give_nothing(self):
        entries = [("192.168.0.30", "aa:bb:cc:00:00:30", "plug")]
        self.assertIsNone(router_login.read_names(RouterLogin("tr064", "http://192.168.0.1:49000", "fritz", "wrong"), tr064_answer(entries)))
        self.assertIsNone(router_login.read_names(RouterLogin("tr064", "http://192.168.0.1:49000", "fritz", SECRET), lambda *a: (0, "")))
        self.assertIsNone(router_login.read_names(RouterLogin("tr064", "http://192.168.0.1:49000", "fritz", SECRET), lambda *a: (200, "<html>not it</html>")))
        self.assertIsNone(router_login.read_names(RouterLogin("tr064", "http://192.168.0.1:49000", "fritz", ""), tr064_answer(entries)), "no password: nothing is asked")

    def test_what_a_router_says_is_cleaned(self):
        entries = [("192.168.0.30", "aa:bb:cc:00:00:30", "o'brien\"s tv"), ("192.168.0.35", "aa:bb:cc:00:00:35", "<script>x</script>"), ("8.8.8.8", "aa:bb:cc:00:00:31", "outside"), ("192.168.0.32", "aa:bb:cc:00:00:32", "n" * 200),
                   ("192.168.0.33", "aa:bb:cc:00:00:33", ""), ("192.168.0.34", "not-a-mac", "ok-name")]
        names = router_login.read_names(RouterLogin("tr064", "http://192.168.0.1:49000", "fritz", SECRET), tr064_answer(entries))
        self.assertEqual(set(names), {"192.168.0.30", "192.168.0.32", "192.168.0.34"})
        self.assertEqual(names["192.168.0.30"], "obriens tv")
        self.assertNotIn("192.168.0.35", names, "markup in a name drops the entry")
        self.assertEqual(len(names["192.168.0.32"]), router_login.MAX_NAME)
        self.assertEqual(names["192.168.0.34"], "ok-name")

    def test_the_number_of_entries_is_bounded(self):
        entries = [(f"192.168.1.{i % 250}", "aa:bb:cc:00:00:01", f"d{i}") for i in range(1000)]
        asked = []

        def http(url, body, headers, user, password):
            asked.append(body)
            return tr064_answer(entries)(url, body, headers, user, password)
        router_login.read_names(RouterLogin("tr064", "http://192.168.0.1:49000", "fritz", SECRET), http)
        self.assertLessEqual(len(asked), router_login.MAX_ENTRIES + 1)

    def test_only_read_only_questions_can_be_built(self):
        for action in ("SetEnable", "Reboot", "X_AVM-DE_SetPassword"):
            with self.assertRaises(ValueError):
                router_login.tr064_request(action)
        for obj, method in (("system", "reboot"), ("uci", "set"), ("file", "write")):
            with self.assertRaises(ValueError):
                router_login.ubus_request("a" * 32, obj, method)

    def test_openwrt_lists_the_leases(self):
        leases = [{"ipaddr": "192.168.1.20", "macaddr": "aa:bb:cc:00:00:20", "hostname": "laptop", "expires": 3000}, {"ipaddr": "192.168.1.21", "macaddr": "aa:bb:cc:00:00:21", "hostname": ""},
                  {"ipaddr": "192.168.1.22", "macaddr": "aa:bb:cc:00:00:22", "hostname": "phone"}, "junk"]
        login = RouterLogin("openwrt", "https://192.168.1.1", "root", SECRET)
        self.assertEqual(router_login.read_names(login, ubus_answer(leases)), {"192.168.1.20": "laptop", "192.168.1.22": "phone"})

    def test_openwrt_refuses_a_wrong_password_and_a_bad_session(self):
        self.assertIsNone(router_login.read_names(RouterLogin("openwrt", "https://192.168.1.1", "root", "wrong"), ubus_answer([])))
        self.assertIsNone(router_login.read_names(RouterLogin("openwrt", "https://192.168.1.1", "root", SECRET), ubus_answer([], session="not-a-session")))
        self.assertIsNone(router_login.read_names(RouterLogin("openwrt", "https://192.168.1.1", "root", SECRET), lambda *a: (200, "not json")))

    def test_the_password_is_not_sent_over_plain_http_to_openwrt(self):
        sent = []
        login = RouterLogin("openwrt", "http://192.168.1.1", "root", SECRET)
        self.assertIsNone(router_login.read_names(login, lambda *a: sent.append(a) or (200, "")))
        self.assertEqual(sent, [], "nothing leaves")
        sent.clear()
        self.assertIsNone(router_login.read_names(RouterLogin("tr064", "http://8.8.8.8", "u", SECRET), lambda *a: sent.append(a) or (200, "")))
        self.assertEqual(sent, [], "not to a public address either")


class Settings(unittest.TestCase):
    def test_everything_is_off_by_default(self):
        s = config_file.parse("{}")
        self.assertFalse(s.router_login or s.router_allow_plain_http)
        self.assertEqual((s.router_kind, s.router_credential, s.router_user, s.router_url, s.router_credential_sealed), ("tr064", "ask", "", "", ""))

    def test_a_complete_file(self):
        sealed = seal_text(TOKEN, SECRET)
        s = config_file.parse(json.dumps({"router_login": True, "router_kind": "openwrt", "router_user": "root", "router_url": "https://192.168.1.1", "router_credential": "sealed",
                                          "router_credential_sealed": sealed, "router_allow_plain_http": False}))
        self.assertEqual((s.router_login, s.router_kind, s.router_user, s.router_credential), (True, "openwrt", "root", "sealed"))

    def test_what_is_wrong_is_refused_with_the_key(self):
        for text, word in (('{"router_kind": "ssh"}', "router_kind"), ('{"router_credential": "plain"}', "router_credential"), ('{"router_login": "yes"}', "router_login"),
                           ('{"router_login": true}', "router_user"), ('{"router_url": "http://8.8.8.8"}', "private"), ('{"router_kind": "openwrt", "router_url": "http://192.168.1.1"}', "https"),
                           ('{"router_user": 5}', "router_user"), ('{"router_credential_sealed": "' + "x" * 600 + '"}', "router_credential_sealed")):
            with self.assertRaises(config_file.ConfigFileError, msg=text) as raised:
                config_file.parse(text)
            self.assertIn(word, str(raised.exception))

    def test_a_clear_password_is_not_a_key(self):
        with self.assertRaises(config_file.ConfigFileError):
            config_file.parse('{"router_password": "secret"}')


class Wiring(unittest.TestCase):
    def run_agent(self, **config):
        clock = [0]
        io = SimIO(lambda: clock[0])
        io.router_answer = {"192.168.0.30": "plug-kitchen"}
        agent = Agent(io, Config(scan_every_s=10, publish_every_s=10, internet_every_s=5, **config))
        for turn in range(8):
            clock[0] = io._t0 + turn * 10_000
            agent.step()
        return agent

    def test_the_router_names_a_device_only_when_the_login_is_on(self):
        plug = lambda agent: next(d for d in agent.inventory.devices.values() if d.ip == "192.168.0.30")   # noqa: E731
        self.assertIsNone(plug(self.run_agent()).hostname, "off by default")
        self.assertEqual(plug(self.run_agent(router_login=True)).hostname, "plug-kitchen")

    def test_a_router_that_does_not_answer_changes_nothing(self):
        clock = [0]
        io = SimIO(lambda: clock[0])
        agent = Agent(io, Config(scan_every_s=10, router_login=True))
        for turn in range(5):
            clock[0] = io._t0 + turn * 10_000
            agent.step()
        self.assertEqual(agent._router_names, {})

    def test_the_real_layer_asks_nothing_without_a_login(self):
        self.assertIsNone(system_io.SystemIO().router_names("192.168.0.1"))
        with mock.patch.object(system_io, "_router_http") as http:
            self.assertIsNone(system_io.SystemIO(router=RouterLogin("tr064", "", "u", SECRET)).router_names("8.8.8.8"))
            http.assert_not_called()

    def test_the_real_layer_uses_the_gateway_when_no_address_was_given(self):
        seen = []
        with mock.patch.object(system_io, "_router_http", side_effect=lambda url, *a: seen.append(url) or (0, "")):
            system_io.SystemIO(router=RouterLogin("tr064", "", "u", SECRET)).router_names("192.168.0.1")
        self.assertEqual(seen, ["http://192.168.0.1:49000/upnp/control/hosts"])


class Cli(unittest.TestCase):
    def test_router_seal_makes_a_seal_that_opens_and_never_prints_the_password(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.dict(os.environ, {router_login.ROUTER_LOGIN_ENV: SECRET}):
            self.assertEqual(cli.main(["router-seal", "--ingest-token", TOKEN]), 0)
        self.assertEqual(open_sealed(TOKEN, out.getvalue().strip()), SECRET)
        self.assertNotIn(SECRET, out.getvalue() + err.getvalue())

    def test_router_seal_needs_a_token_and_a_password(self):
        with contextlib.redirect_stderr(io.StringIO()), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(router_login.ROUTER_LOGIN_ENV, None)
            os.environ.pop("ARMOR_INGEST_TOKEN", None)
            self.assertEqual(cli.main(["router-seal"]), 2)
            with mock.patch.object(cli, "_ask_password", return_value=""):
                self.assertEqual(cli.main(["router-seal", "--ingest-token", TOKEN]), 2)

    def test_the_login_comes_from_the_settings_and_not_without_a_password(self):
        settings = config_file.parse('{"router_login": true, "router_user": "fritz"}')
        with mock.patch.dict(os.environ, {router_login.ROUTER_LOGIN_ENV: SECRET}):
            login, why = cli._router_from_settings(settings, "")
        self.assertEqual((login.user, login.password, login.kind), ("fritz", SECRET, "tr064"))
        with mock.patch.dict(os.environ, {}), mock.patch.object(cli, "_ask_password", return_value=""):
            os.environ.pop(router_login.ROUTER_LOGIN_ENV, None)
            login, why = cli._router_from_settings(settings, "")
        self.assertIsNone(login)
        self.assertIn(router_login.ROUTER_LOGIN_ENV, why)
        self.assertNotIn(SECRET, why)


class Digest(unittest.TestCase):
    """The real HTTP function against a local stand-in that asks for a digest login (RFC 7616, MD5, qop=auth) and answers one JSON body."""

    def serve(self, handler):
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(2)))
        return server

    def test_the_digest_login_does_not_send_the_password(self):
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                self.rfile.read(length)
                auth = self.headers.get("Authorization", "")
                seen.append(auth)
                if not auth.startswith("Digest "):
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Digest realm="stand-in", nonce="abc123", qop="auth", algorithm=MD5')
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                fields = {}
                for part in auth[7:].split(","):
                    key, _, value = part.strip().partition("=")
                    fields[key] = value.strip('"')
                h2 = digest_hex(f"POST:{fields['uri']}")
                expected = digest_hex(f"{STAND_IN_HA1}:{fields['nonce']}:{fields['nc']}:{fields['cnonce']}:{fields['qop']}:{h2}")
                ok = fields.get("response") == expected
                self.send_response(200 if ok else 401)
                payload = b"<NewHostNumberOfEntries>0</NewHostNumberOfEntries>" if ok else b""
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = self.serve(Handler)
        url = f"http://127.0.0.1:{server.server_address[1]}/upnp/control/hosts"
        status, text = system_io._router_http(url, b"<x/>", {"Content-Type": "text/xml"}, "fritz", SECRET)
        self.assertEqual((status, "NewHostNumberOfEntries" in text), (200, True))
        self.assertTrue(all(SECRET not in line for line in seen), "the password itself is never sent")
        status, _ = system_io._router_http(url, b"<x/>", {"Content-Type": "text/xml"}, "fritz", "wrong")
        self.assertEqual(status, 401)

    def test_a_server_that_is_not_there_gives_zero(self):
        self.assertEqual(system_io._router_http("http://127.0.0.1:9/ubus", b"{}", {}, None, None), (0, ""))


if __name__ == "__main__":
    unittest.main()
