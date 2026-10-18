"""The command line of the network watcher: each command with a made-up house in place of the real network (the real one is never touched), what is printed, and what is refused."""
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from armor_network import cli  # noqa: E402
from armor_network.publisher import DeliveryError  # noqa: E402
from armor_network.sim_io import SimIO  # noqa: E402


def house(cidr=None):
    return SimIO(tick_ms=2000)


def run_cli(*argv, env=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.dict(os.environ, env or {}), mock.patch.object(cli.time, "sleep"):
        os.environ.pop("ARMOR_INGEST_TOKEN", None) if env is None else None
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ScanTests(unittest.TestCase):
    def test_the_table_lists_the_interface_the_internet_and_every_device(self):
        with mock.patch.object(cli, "SystemIO", house):
            code, out, err = run_cli("scan", "--no-ports")
        self.assertEqual(code, 0, err)
        self.assertRegex(out, r"Interface .+\s\d+\.\d+\.\d+\.\d+\s+network \d+\.\d+\.\d+\.\d+/\d+\s+router \d+\.\d+\.\d+\.\d+")
        self.assertIn("Internet:", out)
        self.assertRegex(out, r"Devices: [1-9]")
        self.assertIn("address", out)

    def test_json_is_the_message_itself(self):
        with mock.patch.object(cli, "SystemIO", house):
            code, out, _err = run_cli("scan", "--json", "--no-ports", "--node-id", "garage-1")
        self.assertEqual(code, 0)
        message = json.loads(out)
        self.assertEqual(message["node_id"], "garage-1")
        self.assertEqual(message["kind"], "network")
        self.assertTrue(message["devices"])

    def test_an_address_to_skip_is_never_probed_and_does_not_appear(self):
        with mock.patch.object(cli, "SystemIO", house):
            _code, out, _err = run_cli("scan", "--json", "--no-ports")
            first = json.loads(out)["devices"][0]["ip"]
            _code, out, _err = run_cli("scan", "--json", "--no-ports", "--skip", first)
        self.assertNotIn(first, [device["ip"] for device in json.loads(out)["devices"]])

    def test_the_arguments_that_are_wrong_are_refused_before_anything_is_looked_at(self):
        looked = []
        with mock.patch.object(cli, "SystemIO", lambda cidr=None: looked.append(cidr) or house()):
            for arguments in (("scan", "--node-id", "UPPER"), ("scan", "--node-id=-x"), ("scan", "--node-id", "a" * 65), ("scan", "--skip", "1.2.3"), ("scan", "--skip", "a.b.c.d"),
                              ("scan", "--cidr", "8.8.8.0/24"), ("scan", "--cidr", "10.0.0.0/8"), ("scan", "--cidr", "garbage")):
                self.assertEqual(run_cli(*arguments)[0], 2, arguments)
        self.assertEqual(looked, [])

    def test_the_version_and_the_commands_are_there(self):
        with self.assertRaises(SystemExit) as caught:
            run_cli("--version")
        self.assertEqual(caught.exception.code, 0)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                run_cli()
        self.assertEqual(caught.exception.code, 2)


class InternetCommandTests(unittest.TestCase):
    def test_the_state_is_printed_and_the_exit_code_says_whether_the_internet_is_there(self):
        with mock.patch.object(cli, "SystemIO", house):
            code, out, _err = run_cli("internet")
        status = json.loads(out)
        self.assertIn(status["state"], ("up", "degraded", "down", "unknown"))
        self.assertEqual(code, 0 if status["state"] in ("up", "degraded") else 1)


class WatchTests(unittest.TestCase):
    def test_messages_are_printed_one_per_line_and_the_count_stops_the_run(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(cli, "SystemIO", house):
            code, out, err = run_cli("watch", "--count", "2", "--no-public-info", "--data-dir", folder, "--scan-every", "1", "--internet-every", "1", "--no-ports")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(out.splitlines()), 2)
        self.assertTrue(all(json.loads(line)["kind"] == "network" for line in out.splitlines()))

    def test_a_server_and_a_token_go_together_in_both_directions(self):
        self.assertEqual(run_cli("demo", "--server-url", "http://127.0.0.1:1")[0], 2)
        self.assertEqual(run_cli("demo", "--ingest-token", "tok")[0], 2)
        code, _out, err = run_cli("demo", env={"ARMOR_INGEST_TOKEN": "tok"})
        self.assertEqual(code, 2)
        self.assertIn("together", err)

    def test_a_server_across_the_network_over_plain_http_is_warned_about_and_a_local_one_is_not(self):
        for url, warned in (("http://192.168.0.5:8080", True), ("http://127.0.0.1:1", False), ("http://localhost:1", False), ("https://armor.example", False)):
            with mock.patch.object(cli, "deliver", side_effect=DeliveryError("down")), tempfile.TemporaryDirectory() as folder:
                code, _out, err = run_cli("demo", "--count", "1", "--tick-s", "2", "--data-dir", folder, "--server-url", url, "--ingest-token", "tok", "--no-public-info")
            self.assertEqual(code, 0, url)
            self.assertEqual("crosses" in err or "cross the network in the clear" in err, warned, url)
            self.assertIn("UNDELIVERED", err)                                         # a server that is down does not stop the watch

    def test_is_local(self):
        for local in ("http://localhost:8080", "http://127.0.0.1", "http://127.1.2.3:9", "http://[::1]:80", "http://LOCALHOST"):
            self.assertTrue(cli._is_local(local), local)
        for other in ("http://192.168.0.5", "http://127.evil.example", "http://127.0.0.1.evil.example", "http://example.org", "http://10.0.0.1", "http://", "nonsense", "http://0.0.0.0"):
            self.assertFalse(cli._is_local(other), other)

    def test_the_orders_in_the_answer_reach_the_agent(self):
        submitted = []
        agent_class = cli.Agent

        class Spy(agent_class):
            def submit(self, orders):
                submitted.append(orders)
                super().submit(orders)
        with mock.patch.object(cli, "Agent", Spy), mock.patch.object(cli, "deliver", return_value=[]), tempfile.TemporaryDirectory() as folder:
            code, _out, _err = run_cli("demo", "--count", "1", "--tick-s", "2", "--data-dir", folder, "--server-url", "http://127.0.0.1:1", "--ingest-token", "tok", "--no-public-info")
        self.assertEqual(code, 0)
        self.assertEqual(submitted, [[]])

    def test_validation_needs_the_contract_next_to_the_project(self):
        with mock.patch.object(cli, "_validator", return_value=None):
            code, _out, err = run_cli("demo", "--validate", "--count", "1")
        self.assertEqual(code, 2)
        self.assertIn("--validate needs ARMOR-COMMON", err)

    def test_a_message_the_contract_refuses_is_not_sent(self):
        def refuse(topic, message):
            raise ValueError("bad message")
        with mock.patch.object(cli, "_validator", return_value=refuse), mock.patch.object(cli, "deliver") as deliver, tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                run_cli("demo", "--validate", "--count", "1", "--tick-s", "2", "--data-dir", folder, "--server-url", "http://127.0.0.1:1", "--ingest-token", "tok", "--no-public-info")
        deliver.assert_not_called()

    def test_ctrl_c_ends_the_watch_quietly_and_an_error_of_the_agent_is_named(self):
        with mock.patch.object(cli.Agent, "step", side_effect=KeyboardInterrupt), tempfile.TemporaryDirectory() as folder:
            self.assertEqual(run_cli("demo", "--data-dir", folder, "--no-public-info")[0], 0)
        with mock.patch.object(cli.Agent, "step", side_effect=RuntimeError("no default route")), tempfile.TemporaryDirectory() as folder:
            code, _out, err = run_cli("demo", "--data-dir", folder, "--no-public-info")
        self.assertEqual(code, 1)
        self.assertIn("ARMOR_NETWORK=ERROR no default route", err)

    def test_a_demo_probes_nothing_real(self):
        with mock.patch.object(cli, "SystemIO", side_effect=AssertionError("the real network was touched")), tempfile.TemporaryDirectory() as folder:
            code, _out, _err = run_cli("demo", "--count", "1", "--tick-s", "2", "--data-dir", folder, "--no-public-info")
        self.assertEqual(code, 0)

    def test_an_address_that_is_not_an_https_service_is_a_message_not_a_traceback(self):
        for url in ("http://ipinfo.example/json", "ftp://x", "https://u:p@host/", ""):
            code, _out, err = run_cli("demo", "--count", "1", "--public-info-url", url)
            self.assertEqual(code, 2, url)
            self.assertIn("--public-info-url", err)

    def test_a_server_address_with_a_path_or_a_login_is_a_message_not_a_traceback(self):
        for url in ("http://user:pass@127.0.0.1:1", "http://127.0.0.1:1/api", "ftp://x", "nonsense"):
            code, _out, err = run_cli("demo", "--count", "1", "--server-url", url, "--ingest-token", "tok")
            self.assertEqual(code, 2, url)
            self.assertIn("--server-url", err)


class Handler(BaseHTTPRequestHandler):
    seen: list[tuple[str, bytes]] = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        Handler.seen.append((self.headers.get("Authorization", ""), self.rfile.read(length)))
        self.send_response(202)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


class DeliveryEndToEndTests(unittest.TestCase):
    def test_the_demo_house_reaches_a_server_with_its_token(self):
        Handler.seen = []
        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        with tempfile.TemporaryDirectory() as folder:
            code, out, err = run_cli("demo", "--count", "2", "--tick-s", "2", "--data-dir", folder, "--server-url", url, "--ingest-token", "tok-xyz", "--no-public-info")
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "")                                                       # delivered, not printed
        self.assertEqual(len(Handler.seen), 2)
        self.assertTrue(all(auth == "Bearer tok-xyz" for auth, _body in Handler.seen))
        self.assertEqual(json.loads(Handler.seen[0][1])["kind"], "network")
        self.assertNotIn("tok-xyz", err)


if __name__ == "__main__":
    unittest.main()
