"""The real system layer of the network watcher, with the system replaced by stand-ins: nothing here sends a packet or runs a network tool.
What matters most is checked: that nothing outside the private ranges is ever probed, and that what the system prints is read correctly."""
import socket
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import system_io  # noqa: E402
from armor_network.ipnet import ScanRefused  # noqa: E402
from armor_network.system_io import SystemIO  # noqa: E402

IP_ROUTE = "default via 192.168.0.1 dev eth0 proto dhcp src 192.168.0.50 metric 100\n"
IP_ADDR = "2: eth0    inet 192.168.0.50/24 brd 192.168.0.255 scope global dynamic eth0\\       valid_lft 86000sec\n"
PROC_ARP = ("IP address       HW type     Flags       HW address            Mask     Device\n"
            "192.168.0.1      0x1         0x2         aa:bb:cc:00:00:01     *        eth0\n"
            "192.168.0.7      0x1         0x0         aa:bb:cc:00:00:07     *        eth0\n"
            "10.9.9.9         0x1         0x2         aa:bb:cc:00:00:09     *        eth1\n")
PING_OK = "64 bytes from 192.168.0.1: icmp_seq=1 ttl=64 time=1.23 ms\n"
PROC_NET_DEV = ("Inter-|   Receive                                                |  Transmit\n face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
                "    lo: 1000 10 0 0 0 0 0 0 1000 10 0 0 0 0 0 0\n  eth0: 5000 50 0 0 0 0 0 0 7000 70 0 0 0 0 0 0\n")


def fake_run(table):
    """A stand-in for the function that runs a tool: the answer is looked up by the first words of the command, and every command is recorded."""
    calls = []

    def run(command, timeout=6.0):
        calls.append(list(command))
        for prefix, answer in table.items():
            if command[:len(prefix)] == list(prefix):
                return answer
        return ""
    run.calls = calls
    return run


class Recorder:
    """A UDP socket that records what would have been sent."""

    def __init__(self, fail=()):
        self.sent, self.closed, self.fail = [], False, set(fail)

    def setblocking(self, flag):
        pass

    def settimeout(self, value):
        pass

    def sendto(self, data, address):
        if address[0] in self.fail:
            raise BlockingIOError()
        self.sent.append((data, address))

    def close(self):
        self.closed = True


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.object(system_io, "WINDOWS", False)
        patch.start()
        self.addCleanup(patch.stop)

    def read(self, io_object=None, run=None):
        run = run or fake_run({("ip", "route"): IP_ROUTE, ("ip", "-o"): IP_ADDR})
        with mock.patch.object(system_io, "run", run), mock.patch("builtins.open", mock.mock_open(read_data="AA:BB:CC:11:22:33\n")):
            return (io_object or SystemIO()).interface()

    def test_the_interface_of_the_default_route_gives_its_address_network_gateway_and_mac(self):
        info = self.read()
        self.assertEqual((info["name"], info["ip"], info["cidr"], info["gateway"]), ("eth0", "192.168.0.50", "192.168.0.0/24", "192.168.0.1"))
        self.assertEqual(info["mac"], "aa:bb:cc:11:22:33")

    def test_a_network_that_was_given_wins_but_must_be_private_and_small(self):
        self.assertEqual(self.read(SystemIO(cidr="192.168.0.0/25"))["cidr"], "192.168.0.0/25")
        for bad in ("8.8.8.0/24", "192.168.0.0/16", "2001:db8::/32", "nonsense", "10.0.0.0/8"):
            with self.assertRaises(ScanRefused, msg=bad):
                self.read(SystemIO(cidr=bad))

    def test_a_refused_network_is_refused_even_when_this_machine_has_no_route(self):
        with self.assertRaises(ScanRefused):
            self.read(SystemIO(cidr="8.8.8.0/24"), run=fake_run({}))

    def test_a_network_larger_than_a_slash_22_is_looked_at_as_the_slash_24_of_this_machine(self):
        big = "2: eth0    inet 10.0.7.50/16 brd 10.0.255.255 scope global eth0\n"
        run = fake_run({("ip", "route"): "default via 10.0.0.1 dev eth0 proto dhcp\n", ("ip", "-o"): big})
        self.assertEqual(self.read(run=run)["cidr"], "10.0.7.0/24")

    def test_an_address_that_was_given_replaces_the_one_read(self):
        self.assertEqual(self.read(SystemIO(interface_ip="192.168.0.99"))["ip"], "192.168.0.99")

    def test_without_a_route_there_is_no_network(self):
        with self.assertRaises(RuntimeError):
            self.read(run=fake_run({}))

    def test_a_moment_without_a_route_keeps_what_was_known_and_the_answer_is_cached(self):
        probe = SystemIO()
        first = self.read(probe)
        run = fake_run({})
        with mock.patch.object(system_io, "run", run):
            self.assertIs(probe.interface(), first)
            self.assertEqual(run.calls, [])                                           # inside the refresh time nothing is asked again
            probe._info_at = time.monotonic() - system_io.INTERFACE_REFRESH_S - 1
            self.assertIs(probe.interface(), first)                                   # asked again, no route: the old answer stays
            self.assertTrue(run.calls)

    def test_the_address_of_another_interface_is_not_taken_for_the_one_of_the_default_route(self):
        with self.assertRaises(RuntimeError):
            self.read(run=fake_run({("ip", "route"): IP_ROUTE, ("ip", "-o"): "2: eth9    inet 192.168.0.50/24 scope global\n"}))

    def test_a_point_to_point_route_without_a_gateway_still_gives_the_address(self):
        info = self.read(run=fake_run({("ip", "route"): "default dev wwan0 scope link\n", ("ip", "-o"): "3: wwan0    inet 10.64.0.2/30 scope global wwan0\n"}))
        self.assertEqual((info["ip"], info["cidr"], info["gateway"]), ("10.64.0.2", "10.64.0.0/30", None))

    def test_every_host_of_the_network_comes_from_its_cidr(self):
        probe = SystemIO(cidr="192.168.0.0/29")
        with mock.patch.object(system_io, "run", fake_run({("ip", "route"): IP_ROUTE, ("ip", "-o"): IP_ADDR})), mock.patch("builtins.open", mock.mock_open(read_data="AA:BB:CC:11:22:33")):
            self.assertEqual(probe.all_hosts(), [f"192.168.0.{n}" for n in range(1, 7)])


class WindowsInterfaceTests(unittest.TestCase):
    def test_the_windows_tools_are_asked_and_the_adapter_that_owns_the_address_is_named(self):
        route = ("IPv4 Route Table\n  Network Destination        Netmask          Gateway       Interface  Metric\n"
                 "          0.0.0.0          0.0.0.0      192.168.0.1    192.168.0.50     25\n")
        ipconfig = ("Windows IP Configuration\n\nEthernet adapter Ethernet:\n\n   Physical Address. . . . . . . . . : AA-BB-CC-11-22-33\n"
                    "   IPv4 Address. . . . . . . . . . . : 192.168.0.50(Preferred)\n   Subnet Mask . . . . . . . . . . . : 255.255.255.0\n")
        run = fake_run({("route", "print", "-4"): route, ("ipconfig", "/all"): ipconfig})
        with mock.patch.object(system_io, "WINDOWS", True), mock.patch.object(system_io, "run", run):
            info = SystemIO().interface()
        self.assertEqual((info["ip"], info["gateway"], info["cidr"]), ("192.168.0.50", "192.168.0.1", "192.168.0.0/24"))
        self.assertEqual(info["mac"], "aa:bb:cc:11:22:33")
        self.assertIn("Ethernet", info["name"])


class ProbeSafetyTests(unittest.TestCase):
    def test_poke_sends_one_byte_to_the_discard_port_of_private_addresses_only(self):
        sock = Recorder()
        with mock.patch.object(system_io.socket, "socket", return_value=sock):
            SystemIO().poke(["192.168.0.5", "8.8.8.8", "10.0.0.7", "224.0.0.1", "127.0.0.1", "not an address", "172.16.0.9", "172.32.0.9"])
        self.assertEqual(sock.sent, [(b"\x00", ("192.168.0.5", 9)), (b"\x00", ("10.0.0.7", 9)), (b"\x00", ("172.16.0.9", 9))])
        self.assertTrue(sock.closed)

    def test_poke_goes_on_when_one_send_fails_and_always_closes_the_socket(self):
        sock = Recorder(fail={"192.168.0.5"})
        with mock.patch.object(system_io.socket, "socket", return_value=sock):
            SystemIO().poke(["192.168.0.5", "192.168.0.6"])
        self.assertEqual([address for _data, address in sock.sent], [("192.168.0.6", 9)])
        self.assertTrue(sock.closed)

    def test_ping_is_never_run_for_an_address_outside_the_private_ranges(self):
        run = fake_run({("ping",): PING_OK})
        with mock.patch.object(system_io, "WINDOWS", False), mock.patch.object(system_io, "run", run):
            found = SystemIO().ping_many(["192.168.0.1", "1.1.1.1", "8.8.8.8", "10.1.1.1"], timeout_ms=800)
        self.assertEqual(sorted(call[-1] for call in run.calls), ["10.1.1.1", "192.168.0.1"])
        self.assertEqual(sorted(found), ["10.1.1.1", "192.168.0.1"])
        self.assertEqual(found["192.168.0.1"], (1.23, 64))

    def test_ping_commands_are_fixed_argument_lists_for_each_system(self):
        run = fake_run({})
        with mock.patch.object(system_io, "WINDOWS", False), mock.patch.object(system_io, "run", run):
            SystemIO().ping_many(["192.168.0.1"], timeout_ms=3500)
        self.assertEqual(run.calls[0], ["ping", "-c", "1", "-W", "3", "192.168.0.1"])
        run = fake_run({})
        with mock.patch.object(system_io, "WINDOWS", True), mock.patch.object(system_io, "run", run):
            SystemIO().ping_many(["192.168.0.1"], timeout_ms=900)
        self.assertEqual(run.calls[0], ["ping", "-n", "1", "-w", "900", "192.168.0.1"])

    def test_a_device_that_does_not_answer_is_not_listed(self):
        with mock.patch.object(system_io, "run", fake_run({})):
            self.assertEqual(SystemIO().ping_many(["192.168.0.1"]), {})

    def test_the_ports_of_a_public_address_are_never_tried(self):
        with mock.patch.object(system_io.socket, "create_connection") as connect:
            self.assertEqual(SystemIO().scan_ports("8.8.8.8", (80, 443)), {})
            self.assertEqual(SystemIO().scan_ports("127.0.0.1", (80,)), {})
        connect.assert_not_called()

    def test_open_ports_get_their_service_and_what_they_say(self):
        class Conn:
            def __init__(self, port):
                self.port = port

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def settimeout(self, value):
                pass

            def sendall(self, data):
                assert data.startswith(b"GET / HTTP/1.0") and b"Host: 192.168.0.9" in data

            def recv(self, size):
                return b"HTTP/1.0 200 OK\r\nServer: lighttpd\r\n\r\n" if self.port == 80 else b"SSH-2.0-OpenSSH_9.2\r\n"

        def connect(address, timeout):
            if address[1] in (80, 22):
                return Conn(address[1])
            raise ConnectionRefusedError()

        with mock.patch.object(system_io.socket, "create_connection", side_effect=connect):
            found = SystemIO().scan_ports("192.168.0.9", (22, 80, 443, 8080))
        self.assertEqual(sorted(found), [22, 80])
        self.assertEqual(found[22][0], "ssh")
        self.assertIn("OpenSSH", found[22][1] or "")
        self.assertIn("lighttpd", found[80][1] or "")

    def test_a_banner_that_cannot_be_read_is_none_not_an_error(self):
        class Broken:
            def settimeout(self, value):
                pass

            def sendall(self, data):
                raise OSError()

            def recv(self, size):
                raise OSError()

        for port in (80, 22, 9999):
            self.assertIsNone(SystemIO._banner(Broken(), "192.168.0.9", port))

    def test_the_gateway_is_there_if_it_answers_or_refuses_and_not_if_it_is_silent(self):
        probe = SystemIO()
        with mock.patch.object(system_io, "run", fake_run({("ping",): PING_OK})):
            self.assertTrue(probe.probe_gateway("192.168.0.1"))
        with mock.patch.object(system_io, "run", fake_run({})), mock.patch.object(system_io.socket, "create_connection", side_effect=ConnectionRefusedError()):
            self.assertTrue(probe.probe_gateway("192.168.0.1"))
        attempts = []

        def silent(address, timeout):
            attempts.append(address[1])
            raise socket.timeout()
        with mock.patch.object(system_io, "run", fake_run({})), mock.patch.object(system_io.socket, "create_connection", side_effect=silent):
            self.assertFalse(probe.probe_gateway("192.168.0.1"))
        self.assertEqual(attempts, [80, 443, 53])

    def test_the_internet_check_asks_exactly_the_four_documented_things(self):
        sockets = []

        class Dns:
            def __init__(self, *args):
                sockets.append(self)
                self.sent = None

            def settimeout(self, value):
                pass

            def sendto(self, data, address):
                self.sent = address

            def recvfrom(self, size):
                raise OSError("no answer")

            def close(self):
                pass

        class Closing:
            def close(self):
                pass

        with mock.patch.object(system_io.socket, "create_connection", return_value=Closing()) as connect, mock.patch.object(system_io.socket, "socket", side_effect=Dns), \
                mock.patch.object(system_io, "urlopen", side_effect=OSError("offline")):
            results = SystemIO().probe_internet(timeout=0.2)
        self.assertEqual([(r.target, r.kind) for r in results], [("1.1.1.1:443", "tcp"), ("1.1.1.1", "dns"), ("8.8.8.8", "dns"), ("connectivitycheck.gstatic.com", "http")])
        self.assertEqual([r.ok for r in results], [True, False, False, False])
        self.assertEqual(connect.call_args.args[0], ("1.1.1.1", 443))
        self.assertEqual(sorted(s.sent for s in sockets), [("1.1.1.1", 53), ("8.8.8.8", 53)])


class ReadingTheSystemTests(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.object(system_io, "WINDOWS", False)
        patch.start()
        self.addCleanup(patch.stop)
        self.probe = SystemIO(cidr="192.168.0.0/24", interface_ip="192.168.0.50")
        self.probe._info = {"name": "eth0", "ip": "192.168.0.50", "cidr": "192.168.0.0/24", "gateway": "192.168.0.1", "mac": None}
        self.probe._info_at = time.monotonic()

    def test_the_neighbour_table_keeps_the_resolved_neighbours_of_this_network_only(self):
        with mock.patch("builtins.open", mock.mock_open(read_data=PROC_ARP)):
            self.assertEqual(self.probe.arp_table(), {"192.168.0.1": "aa:bb:cc:00:00:01"})

    def test_without_proc_the_neighbours_come_from_ip_neigh(self):
        with mock.patch("builtins.open", side_effect=OSError()), mock.patch.object(system_io, "run", fake_run({("ip", "neigh"): "192.168.0.1 dev eth0 lladdr aa:bb:cc:00:00:01 REACHABLE\n192.168.0.2 dev eth0  FAILED\n"})):
            self.assertEqual(self.probe.arp_table(), {"192.168.0.1": "aa:bb:cc:00:00:01"})

    def test_traffic_is_the_counters_of_this_interface(self):
        with mock.patch("builtins.open", mock.mock_open(read_data=PROC_NET_DEV)):
            self.assertEqual(self.probe.traffic(), (5000, 7000))
        with mock.patch("builtins.open", side_effect=OSError()):
            self.assertIsNone(self.probe.traffic())

    def test_the_route_to_a_device_is_the_text_of_the_systems_tool_with_a_fallback_and_a_hint(self):
        run = fake_run({("traceroute",): " 1  192.168.0.1  0.5 ms\n"})
        with mock.patch.object(system_io, "run", run):
            self.assertEqual(self.probe.traceroute("192.168.0.9"), "1  192.168.0.1  0.5 ms")
        self.assertEqual(run.calls[0], ["traceroute", "-n", "-m", "12", "-w", "1", "192.168.0.9"])
        run = fake_run({("tracepath",): "1?: [LOCALHOST]\n"})
        with mock.patch.object(system_io, "run", run):
            self.assertIn("LOCALHOST", self.probe.traceroute("192.168.0.9"))
        with mock.patch.object(system_io, "run", fake_run({})):
            self.assertIn("apt install traceroute", self.probe.traceroute("192.168.0.9"))

    def test_a_name_is_looked_up_only_for_private_addresses(self):
        with mock.patch.object(system_io.socket, "gethostbyaddr") as lookup, mock.patch.object(system_io.socket, "socket") as udp:
            self.assertIsNone(self.probe.resolve("8.8.8.8"))
        lookup.assert_not_called()
        udp.assert_not_called()

    def test_the_reverse_name_is_shortened_and_netbios_is_the_second_chance(self):
        with mock.patch.object(system_io.socket, "gethostbyaddr", return_value=("printer.lan.example", [], ["192.168.0.9"])):
            self.assertEqual(self.probe.resolve("192.168.0.9"), "printer")
        with mock.patch.object(system_io.socket, "gethostbyaddr", return_value=("192.168.0.9", [], [])), mock.patch.object(system_io.socket, "socket") as udp:
            udp.return_value.recvfrom.side_effect = OSError("silent")
            self.assertIsNone(self.probe.resolve("192.168.0.9"))
            udp.return_value.close.assert_called_once()

    def test_an_answer_from_another_address_is_not_taken_for_the_device(self):
        with mock.patch.object(system_io.socket, "gethostbyaddr", side_effect=OSError()), mock.patch.object(system_io.socket, "socket") as udp, \
                mock.patch.object(system_io.parsers, "parse_nbstat", return_value="IMPOSTOR"):
            udp.return_value.recvfrom.return_value = (b"data", ("192.168.0.77", 137))
            self.assertIsNone(self.probe.resolve("192.168.0.9"))
            udp.return_value.recvfrom.return_value = (b"data", ("192.168.0.9", 137))
            self.assertEqual(self.probe.resolve("192.168.0.9"), "IMPOSTOR")

    def test_discovery_gives_nothing_when_the_multicast_questions_cannot_be_sent(self):
        with mock.patch.object(system_io.socket, "socket") as udp:
            udp.return_value.sendto.side_effect = OSError("no multicast")
            self.assertEqual(self.probe.discover(listen_s=0.05), {})
            udp.return_value.close.assert_called_once()

    def test_discovery_ignores_answers_from_outside_the_private_ranges(self):
        sock = mock.Mock()
        answers = [(b"HTTP/1.1 200 OK\r\nST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n\r\n", ("8.8.8.8", 1900)),
                   (b"HTTP/1.1 200 OK\r\nST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n\r\n", ("192.168.0.20", 1900))]
        calls = {"n": 0}

        def receive(size):
            calls["n"] += 1
            if answers:
                return answers.pop(0)
            raise socket.timeout()
        sock.recvfrom.side_effect = receive
        with mock.patch.object(system_io.socket, "socket", return_value=sock):
            found = self.probe.discover(listen_s=0.2)
        self.assertEqual(list(found), ["192.168.0.20"])
        self.assertEqual(found["192.168.0.20"]["services"], ["MediaRenderer"])

    def test_the_wake_up_packet_goes_through_the_one_function_that_sends_it(self):
        with mock.patch.object(system_io, "send_magic_packet") as send:
            message = self.probe.wake("aa:bb:cc:00:00:01", "192.168.0.255")
        send.assert_called_once_with("aa:bb:cc:00:00:01", "192.168.0.255")
        self.assertIn("aa:bb:cc:00:00:01", message)

    def test_the_clock_and_the_sleep_are_the_real_ones(self):
        self.assertAlmostEqual(self.probe.now_ms() / 1000, time.time(), delta=2)
        with mock.patch.object(system_io.time, "sleep") as sleep:
            self.probe.sleep(0.25)
        sleep.assert_called_once_with(0.25)


if __name__ == "__main__":
    unittest.main()
