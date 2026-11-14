"""The file with the settings of the checks that are off by default: every key optional and off, strict about what it accepts, and the flags win over it."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from armor_network import cli, config_file  # noqa: E402
from armor_network.sim_io import SimIO  # noqa: E402


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.dict(os.environ, {}), mock.patch.object(cli.time, "sleep"):
        os.environ.pop("ARMOR_INGEST_TOKEN", None)
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Parsing(unittest.TestCase):
    def test_everything_is_off_when_the_file_says_nothing(self):
        self.assertEqual(config_file.parse("{}"), config_file.FileSettings())
        defaults = config_file.FileSettings()
        self.assertFalse(defaults.rogue_dhcp or defaults.router_igd)
        self.assertEqual((defaults.allow_dhcp, defaults.dhcp_interface), ([], ""))

    def test_a_complete_file(self):
        settings = config_file.parse('{"rogue_dhcp": true, "allow_dhcp": ["192.168.0.2", "fe80::1"], "router_igd": true, "dhcp_interface": "192.168.0.10"}')
        self.assertEqual((settings.rogue_dhcp, settings.router_igd, settings.dhcp_interface), (True, True, "192.168.0.10"))
        self.assertEqual(settings.allow_dhcp, ["192.168.0.2", "fe80::1"])

    def test_what_is_wrong_is_refused_with_the_key(self):
        for text, word in (("[]", "object"), ("nope", "JSON"), ('{"rogue": true}', "unknown key"), ('{"rogue_dhcp": "yes"}', "rogue_dhcp"), ('{"router_igd": 1}', "router_igd"),
                           ('{"allow_dhcp": "192.168.0.2"}', "allow_dhcp"), ('{"allow_dhcp": ["not-an-address"]}', "not an address"), ('{"allow_dhcp": ' + str(["10.0.0.1"] * 33).replace("'", '"') + "}", "at most"),
                           ('{"dhcp_interface": "eth0"}', "dhcp_interface"), ('{"dhcp_interface": "8.8.8.8"}', "dhcp_interface"), ('{"dhcp_interface": 5}', "dhcp_interface")):
            with self.assertRaises(config_file.ConfigFileError, msg=text) as caught:
                config_file.parse(text)
            self.assertIn(word, str(caught.exception))

    def test_a_missing_file_is_the_defaults_unless_it_was_asked_for(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            self.assertEqual(config_file.load(path, required=False), config_file.FileSettings())
            with self.assertRaises(config_file.ConfigFileError):
                config_file.load(path, required=True)
            path.write_bytes(b" " * (config_file.MAX_BYTES + 1))
            with self.assertRaises(config_file.ConfigFileError):
                config_file.load(path, required=False)
            path.write_bytes(b"\xff\xfe")
            with self.assertRaises(config_file.ConfigFileError):
                config_file.load(path, required=False)


class OnTheCommandLine(unittest.TestCase):
    def seen_config(self, *argv, file_text=None):
        captured = {}

        class Spy:
            def __init__(self, io, config):
                captured["config"] = config

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(cli, "Agent", Spy), mock.patch.object(cli, "_run_loop", lambda agent, args, forever: 0), \
                mock.patch.object(cli, "SystemIO", lambda cidr=None, dhcp_local=None: SimIO(tick_ms=2000)):
            data = Path(directory) / "data"
            data.mkdir()
            if file_text is not None:
                (data / "config.json").write_text(file_text, encoding="utf-8")
            code, _out, err = run("watch", "--data-dir", str(data), *argv)
        return code, err, captured.get("config")

    def test_without_a_file_every_check_is_off(self):
        code, _err, config = self.seen_config()
        self.assertEqual(code, 0)
        self.assertFalse(config.rogue_dhcp or config.router_igd)
        self.assertEqual(config.dhcp_allowed, set())

    def test_the_file_in_the_data_directory_turns_the_checks_on(self):
        _code, _err, config = self.seen_config(file_text='{"rogue_dhcp": true, "router_igd": true, "allow_dhcp": ["192.168.0.9"]}')
        self.assertTrue(config.rogue_dhcp and config.router_igd)
        self.assertEqual(config.dhcp_allowed, {"192.168.0.9"})

    def test_a_flag_wins_over_the_file(self):
        _code, _err, config = self.seen_config("--allow-dhcp", "192.168.0.7", file_text='{"allow_dhcp": ["192.168.0.9"]}')
        self.assertEqual(config.dhcp_allowed, {"192.168.0.7"})
        _code, _err, config = self.seen_config("--rogue-dhcp")
        self.assertTrue(config.rogue_dhcp)

    def test_a_broken_file_stops_the_start_and_says_why(self):
        code, err, config = self.seen_config(file_text='{"rogue_dhcp": "yes"}')
        self.assertEqual(code, 2)
        self.assertIn("config:", err)
        self.assertIsNone(config)

    def test_a_file_given_by_name_must_exist(self):
        code, err, _config = self.seen_config("--config", "/nonexistent/armor-network.json")
        self.assertEqual(code, 2)
        self.assertIn("does not exist", err)

    def test_the_address_of_the_file_is_checked_like_the_flag(self):
        code, err, _config = self.seen_config(file_text='{"dhcp_interface": "8.8.8.8"}')
        self.assertEqual(code, 2)
        self.assertIn("config:", err)
        code, _err, _config = self.seen_config(file_text='{"dhcp_interface": "192.168.0.10"}')
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
