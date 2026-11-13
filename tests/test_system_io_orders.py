"""The real system layer, the manual orders and the traffic counters, with the system replaced by stand-ins: the commands asked for on each system, what is done when a tool is missing,
and that the counters read from the right place. Nothing here runs a network tool or sends a packet."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import system_io  # noqa: E402
from armor_network.system_io import SystemIO  # noqa: E402

NETSTAT_E = """Interface Statistics

                           Received            Sent

Bytes                    123456789        98765432
Unicast packets             100000           90000
"""


def recording_run(answers):
    """A stand-in for the function that runs a tool: the answer is taken in turn, and every command and timeout is recorded."""
    calls = []
    queue = list(answers)

    def run(command, timeout=6.0):
        calls.append((list(command), timeout))
        return queue.pop(0) if queue else ""
    run.calls = calls
    return run


class TracerouteTests(unittest.TestCase):
    def test_linux_asks_traceroute_first_and_tracepath_when_it_prints_nothing(self):
        run = recording_run(["", " 1  192.168.0.1  1.2 ms\n"])
        with mock.patch.object(system_io, "WINDOWS", False), mock.patch.object(system_io, "run", run):
            text = SystemIO().traceroute("192.168.0.50")
        self.assertEqual(text, "1  192.168.0.1  1.2 ms")
        self.assertEqual([call[0][0] for call in run.calls], ["traceroute", "tracepath"])
        self.assertEqual(run.calls[0][0], ["traceroute", "-n", "-m", "12", "-w", "1", "192.168.0.50"])
        self.assertEqual(run.calls[1][0], ["tracepath", "-n", "-m", "12", "192.168.0.50"])
        self.assertTrue(all(call[1] == 40 for call in run.calls), "a trace may take long, but never forever")

    def test_linux_says_what_to_install_when_neither_tool_prints_anything(self):
        with mock.patch.object(system_io, "WINDOWS", False), mock.patch.object(system_io, "run", recording_run([])):
            self.assertIn("apt install traceroute", SystemIO().traceroute("192.168.0.50"))

    def test_windows_asks_tracert_once_and_has_no_second_tool(self):
        run = recording_run(["  1    <1 ms  192.168.0.1\n"])
        with mock.patch.object(system_io, "WINDOWS", True), mock.patch.object(system_io, "run", run):
            self.assertEqual(SystemIO().traceroute("192.168.0.50"), "1    <1 ms  192.168.0.1")
        self.assertEqual(run.calls[0][0], ["tracert", "-d", "-h", "12", "-w", "600", "192.168.0.50"])
        with mock.patch.object(system_io, "WINDOWS", True), mock.patch.object(system_io, "run", recording_run([])):
            self.assertIn("no traceroute tool", SystemIO().traceroute("192.168.0.50"))


class TrafficTests(unittest.TestCase):
    def test_windows_reads_the_sum_of_the_interfaces_from_netstat(self):
        run = recording_run([NETSTAT_E])
        with mock.patch.object(system_io, "WINDOWS", True), mock.patch.object(system_io, "run", run):
            self.assertEqual(SystemIO().traffic(), (123456789, 98765432))
        self.assertEqual(run.calls[0][0], ["netstat", "-e"])

    def test_linux_reads_the_counters_of_its_own_interface_and_none_when_the_file_is_missing(self):
        proc = ("Inter-|   Receive                                                |  Transmit\n face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
                "  eth0: 5000 50 0 0 0 0 0 0 7000 70 0 0 0 0 0 0\n")
        io = SystemIO()
        with mock.patch.object(system_io, "WINDOWS", False), mock.patch.object(SystemIO, "interface", return_value={"name": "eth0"}), mock.patch("builtins.open", mock.mock_open(read_data=proc)):
            self.assertEqual(io.traffic(), (5000, 7000))
        with mock.patch.object(system_io, "WINDOWS", False), mock.patch.object(SystemIO, "interface", return_value={"name": "eth0"}), mock.patch("builtins.open", side_effect=OSError("no such file")):
            self.assertIsNone(io.traffic())


class DelegationTests(unittest.TestCase):
    def test_the_manual_orders_are_handed_to_their_own_functions_with_the_arguments_as_given(self):
        io = SystemIO()
        with mock.patch.object(system_io, "fetch_public_info", return_value={"ip": "203.0.113.5"}) as info, \
                mock.patch.object(system_io, "resolve_dns_name", return_value=["192.168.0.9"]) as resolve, \
                mock.patch.object(system_io, "http_look", return_value={"status": 200}) as look, \
                mock.patch.object(system_io, "inspect_web", return_value={"title": "x"}) as inspect, \
                mock.patch.object(system_io, "send_magic_packet") as wake:
            self.assertEqual(io.public_info("https://example.org/ip"), {"ip": "203.0.113.5"})
            self.assertEqual(io.resolve_name("armor.lan"), ["192.168.0.9"])
            self.assertEqual(io.http_look("192.168.0.9", 80), {"status": 200})
            self.assertEqual(io.inspect_web("192.168.0.9", 443, "admin", None), {"title": "x"})
            text = io.wake("aa:bb:cc:00:00:01", "192.168.0.255")
        info.assert_called_once_with("https://example.org/ip")
        resolve.assert_called_once_with("armor.lan")
        look.assert_called_once_with("192.168.0.9", 80)
        inspect.assert_called_once_with("192.168.0.9", 443, "admin", None)
        wake.assert_called_once_with("aa:bb:cc:00:00:01", "192.168.0.255")
        self.assertEqual(text, "a wake-up packet for aa:bb:cc:00:00:01 was broadcast on 192.168.0.255")


if __name__ == "__main__":
    unittest.main()
