"""The findings in the agent and in the real network layer: a risky port and a second DHCP server told once as events, the router counters read only when asked for, and the DHCP
question read through a stand-in socket (never answered with a request). Nothing here touches a network.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later."""
import socket
import struct
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
COMMON = ROOT.parent / "ARMOR-COMMON" / "src"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from armor_network import rogue_dhcp, system_io  # noqa: E402
from armor_network.agent import Agent, Config  # noqa: E402
from armor_network.sim_io import SimIO  # noqa: E402
from armor_network.system_io import SystemIO  # noqa: E402

try:
    from armor_common import validate_network_message
except ImportError:   # the contract is not next to this checkout
    validate_network_message = None


class Clock:
    now = 0

    def __call__(self):
        return self.now


def run(agent, io, clock, turns=14):
    """Walk the scripted house for `turns` ten-second turns; every event of every message, in order."""
    events, messages = [], []
    for turn in range(turns):
        clock.now = io._t0 + turn * 10_000
        message = agent.step()
        if message is not None:
            messages.append(message)
            events = message["events"]
    return events, messages


def make(**config):
    clock = Clock()
    io = SimIO(clock)
    agent = Agent(io, Config(scan_every_s=10, publish_every_s=10, internet_every_s=5, **config))
    return agent, io, clock


class RiskyPorts(unittest.TestCase):
    def test_a_risky_port_that_is_open_is_told_once_with_its_recommendation(self):
        agent, io, clock = make()
        events, messages = run(agent, io, clock, turns=16)
        risky = [e for e in events if e["kind"] == "risky_port"]
        self.assertTrue(risky, "the telnet port of the webcam is a finding")
        webcam = [e for e in risky if e["device_id"] == "de:ad:be:ef:00:77" and e["port"] == 23]
        self.assertEqual(len(webcam), 1, "once, not on every sweep")
        self.assertEqual(webcam[0]["recommendation"], "close_telnet")
        self.assertIn("23", webcam[0]["detail"])
        self.assertLessEqual(len({e["id"] for e in risky}), len(risky))
        if validate_network_message is not None:
            for message in messages:
                validate_network_message(f"armor/network/{message['node_id']}/state", message)

    def test_a_finding_that_goes_and_comes_back_is_told_again(self):
        agent, io, clock = make()
        run(agent, io, clock, turns=8)
        self.assertIn("de:ad:be:ef:00:77:23", {f"{e['device_id']}:{e['port']}" for e in agent.log.events if e["kind"] == "risky_port"})
        agent._reported_findings.clear()   # as if the port had closed and opened again
        agent._findings(io._t0 + 200_000, io.interface())
        self.assertEqual(len([e for e in agent.log.events if e["kind"] == "risky_port" and e["device_id"] == "de:ad:be:ef:00:77"]), 2)


class RogueDhcp(unittest.TestCase):
    def test_it_asks_nothing_unless_it_is_switched_on(self):
        agent, io, clock = make()
        io.dhcp_offers = mock.Mock(side_effect=AssertionError("the network must not be asked"))
        events, _ = run(agent, io, clock, turns=4)
        self.assertEqual([e for e in events if e["kind"] == "rogue_dhcp"], [])

    def test_the_router_is_not_a_rogue_server_and_another_one_is_told_once(self):
        agent, io, clock = make(rogue_dhcp=True, rogue_dhcp_every_s=10)
        io.dhcp_servers = [{"server": "192.168.0.1", "offered": "192.168.0.50"}, {"server": "192.168.0.99", "offered": "10.0.0.5"}]
        events, messages = run(agent, io, clock, turns=6)
        rogue = [e for e in events if e["kind"] == "rogue_dhcp"]
        self.assertEqual([e["server"] for e in rogue], ["192.168.0.99"])
        self.assertEqual(rogue[0]["recommendation"], "find_the_dhcp_server")
        self.assertNotIn("device_id", rogue[0])
        if validate_network_message is not None:
            for message in messages:
                validate_network_message(f"armor/network/{message['node_id']}/state", message)

    def test_a_server_the_person_named_belongs(self):
        agent, io, clock = make(rogue_dhcp=True, rogue_dhcp_every_s=10, dhcp_allowed={"192.168.0.99"})
        io.dhcp_servers = [{"server": "192.168.0.99", "offered": "192.168.0.50"}]
        events, _ = run(agent, io, clock, turns=4)
        self.assertEqual([e for e in events if e["kind"] == "rogue_dhcp"], [])

    def test_the_question_is_put_at_the_pace_set_and_not_every_turn(self):
        agent, io, clock = make(rogue_dhcp=True, rogue_dhcp_every_s=600)
        io.dhcp_offers = mock.Mock(return_value=[])
        run(agent, io, clock, turns=8)
        self.assertEqual(io.dhcp_offers.call_count, 1)


class RouterCounters(unittest.TestCase):
    def test_the_counters_of_the_router_are_used_only_when_asked_for(self):
        agent, io, clock = make()
        io.igd_totals = mock.Mock(side_effect=AssertionError("the router must not be asked"))
        run(agent, io, clock, turns=4)
        agent, io, clock = make(router_igd=True, traffic_every_s=5)
        io.igd_answer = (1_000_000, 250_000)
        _, messages = run(agent, io, clock, turns=4)
        interface = messages[-1]["interface"]
        self.assertGreater(interface["rx_bps"], 0)
        self.assertGreater(interface["tx_bps"], 0)

    def test_a_router_that_does_not_answer_leaves_the_counters_of_the_system(self):
        agent, io, clock = make(router_igd=True, traffic_every_s=5)
        io.igd_answer = None
        _, messages = run(agent, io, clock, turns=4)
        self.assertIn("rx_bps", messages[-1]["interface"], "the system counters are still there")


def offer_packet(xid, server="192.168.0.99"):
    def ip(text):
        return bytes(int(part) for part in text.split("."))
    header = struct.pack("!BBBBIHH4s4s4s4s16s64s128s", 2, 1, 6, 0, xid, 0, 0x8000, b"\0" * 4, ip("192.168.0.50"), b"\0" * 4, b"\0" * 4, bytes(6) + b"\0" * 10, b"\0" * 64, b"\0" * 128)
    return header + rogue_dhcp.MAGIC_COOKIE + bytes([53, 1, 2, 54, 4]) + ip(server) + bytes([255])


class FakeDhcpSocket:
    """A socket that, once the question is sent, answers with the offers it was given (for the transaction of the question), and records what happens."""

    def __init__(self, servers, bind_error=None):
        self.servers, self.bind_error, self.sent, self.bound, self.closed, self._xid = list(servers), bind_error, [], None, False, None

    def setsockopt(self, *args):
        pass

    def settimeout(self, value):
        pass

    def bind(self, address):
        if self.bind_error:
            raise self.bind_error
        self.bound = address

    def sendto(self, data, address):
        self.sent.append((data, address))
        self._xid = struct.unpack("!I", data[4:8])[0]

    def recvfrom(self, size):
        if self.servers:
            return offer_packet(self._xid, self.servers.pop(0)), ("192.168.0.99", 67)
        raise socket.timeout()

    def close(self):
        self.closed = True


class SystemDhcp(unittest.TestCase):
    def io(self):
        io = SystemIO()
        io.interface = lambda: {"name": "eth0", "ip": "192.168.0.10", "cidr": "192.168.0.0/24", "gateway": "192.168.0.1", "mac": "c0:35:32:d6:35:77"}
        return io

    def test_one_question_on_the_broadcast_address_and_the_offers_read(self):
        fake = FakeDhcpSocket(["192.168.0.99", "8.8.8.8"])
        with mock.patch.object(system_io.socket, "socket", return_value=fake):
            offers = self.io().dhcp_offers(listen_s=0.2)
        self.assertEqual([o["server"] for o in offers], ["192.168.0.99"], "an offer from a public address is not believed")
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(fake.sent[0][1], ("255.255.255.255", 67))
        self.assertEqual(fake.sent[0][0][0], 1, "a DISCOVER, never a REQUEST")
        self.assertEqual(fake.bound, ("", 68))
        self.assertTrue(fake.closed)

    def test_without_permission_the_answer_is_an_empty_list(self):
        fake = FakeDhcpSocket([], bind_error=PermissionError("not allowed"))
        with mock.patch.object(system_io.socket, "socket", return_value=fake):
            self.assertEqual(self.io().dhcp_offers(listen_s=0.2), [])
        self.assertEqual(fake.sent, [])
        self.assertTrue(fake.closed)

    def test_an_interface_with_no_mac_asks_nothing(self):
        io = self.io()
        io.interface = lambda: {"name": "eth0", "ip": "192.168.0.10", "cidr": "192.168.0.0/24"}
        with mock.patch.object(system_io.socket, "socket", side_effect=AssertionError("no socket")):
            self.assertEqual(io.dhcp_offers(), [])


DESCRIPTION = ("<root><device><serviceList><service><serviceType>urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1</serviceType>"
               "<controlURL>/ctl/CmnIfCfg</controlURL></service></serviceList></device></root>")


class SystemIgd(unittest.TestCase):
    def test_the_totals_of_the_router_from_its_description(self):
        io = SystemIO()
        io._locations["192.168.0.1"] = "http://192.168.0.1:5000/rootDesc.xml"
        asked = []

        class Response:
            def __init__(self, text):
                self.text = text

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size=-1):
                return self.text.encode()

        def urlopen(request, timeout=0):
            asked.append(request.get_header("Soapaction"))
            name = "NewTotalBytesReceived" if "Received" in request.get_header("Soapaction") else "NewTotalBytesSent"
            return Response(f"<r><{name}>{1234 if name.endswith('Received') else 99}</{name}></r>")
        with mock.patch.object(system_io, "_open", return_value=Response(DESCRIPTION)), mock.patch.object(system_io, "urlopen", urlopen):
            self.assertEqual(io.igd_totals("192.168.0.1"), (1234, 99))
        self.assertEqual(len(asked), 2, "only the two read-only questions")

    def test_a_router_that_never_announced_itself_is_not_asked(self):
        with mock.patch.object(system_io, "_open", side_effect=AssertionError("no request")):
            self.assertIsNone(SystemIO().igd_totals("192.168.0.1"))


if __name__ == "__main__":
    unittest.main()
