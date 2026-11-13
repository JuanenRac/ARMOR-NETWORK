"""The agent against the scripted network on the edges of its orders and its readings: an order that breaks, a ping nobody answers, a login that is withheld or not sent because the address
changed hands, a machine with no name and a counter that went down. Nothing here touches a network."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
COMMON = ROOT.parent / "ARMOR-COMMON" / "src"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from armor_network import agent as agent_module  # noqa: E402
from armor_network import orders  # noqa: E402
from armor_network.agent import Agent, Config  # noqa: E402
from armor_network.sim_io import SimIO  # noqa: E402


class Clock:
    now = 0

    def __call__(self):
        return self.now


def started():
    clock = Clock()
    io = SimIO(clock)
    agent = Agent(io, Config(scan_every_s=10, publish_every_s=10, internet_every_s=5))
    clock.now = io._t0
    agent.step()
    clock.now = io._t0 + 10_000
    return agent, io, clock


def results_of(agent, *order_list):
    agent.submit(list(order_list))
    message = agent.step()
    return {result["id"]: result for result in message["results"]}


class Orders(unittest.TestCase):
    def test_an_order_that_breaks_is_an_answer_and_the_node_goes_on(self):
        agent, io, _ = started()
        scan = io.ping_many

        def broken(ips):
            if list(ips) == ["192.168.0.50"]:
                raise RuntimeError("socket gone")
            return scan(ips)

        io.ping_many = broken
        result = results_of(agent, orders.Order("p1", "ping", ip="192.168.0.50"))["p1"]
        self.assertFalse(result["ok"])
        self.assertIn("the order failed: socket gone", result["output"])

    def test_a_ping_nobody_answers_says_so(self):
        agent, io, _ = started()
        io.ping_many = lambda ips: {}
        result = results_of(agent, orders.Order("p1", "ping", ip="192.168.0.50"))["p1"]
        self.assertEqual((result["ok"], result["output"]), (False, "192.168.0.50 did not answer"))

    def test_a_ping_answer_with_a_ttl_says_it(self):
        agent, io, _ = started()
        io.ping_many = lambda ips: {ip: (3.25, 64) for ip in ips}
        result = results_of(agent, orders.Order("p1", "ping", ip="192.168.0.50"))["p1"]
        self.assertTrue(result["ok"])
        self.assertIn("(TTL 64)", result["output"])
        io.ping_many = lambda ips: {ip: (3.25, 0) for ip in ips}
        self.assertNotIn("TTL", results_of(agent, orders.Order("p2", "ping", ip="192.168.0.50"))["p2"]["output"])

    def test_a_login_that_the_server_withheld_is_not_used_and_the_note_says_why(self):
        agent, io, _ = started()
        calls = []
        io.inspect_web = lambda ip, port, user, password: calls.append((user, password)) or {"ok": True, "output": "looked"}
        result = results_of(agent, orders.Order("w1", "inspect", ip="192.168.0.50", user="admin", password="p", login_withheld=True))["w1"]
        self.assertIn("would travel to this node in the clear", result["output"])

    def test_a_login_is_not_sent_when_two_machines_claimed_the_address_a_moment_ago(self):
        agent, io, clock = started()
        calls = []
        io.inspect_web = lambda ip, port, user, password: calls.append((user, password)) or {"ok": True, "output": "looked"}
        io.arp_table = lambda: {}
        agent.log.events.append({"kind": "arp_conflict", "at_ms": clock.now, "detail": "192.168.0.50 claimed by two machines"})
        result = results_of(agent, orders.Order("w1", "inspect", ip="192.168.0.50", mac="aa:aa:aa:aa:aa:aa", user="admin", password="p"))["w1"]
        self.assertEqual(calls, [(None, None)])
        self.assertIn("two machines claimed 192.168.0.50", result["output"])

    def test_a_note_for_the_mac_that_answers_is_added_when_the_device_changed(self):
        agent, io, _ = started()
        io.inspect_web = lambda ip, port, user, password: {"ok": True, "output": "looked"}
        io.arp_table = lambda: {"192.168.0.50": "aa:aa:aa:aa:aa:aa"}
        result = results_of(agent, orders.Order("w1", "inspect", ip="192.168.0.50", mac="bb:bb:bb:bb:bb:bb", user="admin", password="p"))["w1"]
        self.assertIn("is answered by aa:aa:aa:aa:aa:aa", result["output"])


class Readings(unittest.TestCase):
    def test_a_machine_with_no_name_is_still_listed(self):
        agent, io, clock = started()
        with mock.patch.object(agent_module.socket, "gethostname", side_effect=OSError("no name")):
            clock.now += 10_000
            message = agent.step()
        self.assertIsNotNone(message)

    def test_a_counter_that_went_down_makes_the_rate_unknown_until_the_next_reading(self):
        agent, io, clock = started()
        readings = iter([(1_000_000, 500_000), (2_000_000, 900_000), (100, 50), (5_100, 2_050)])
        io.traffic = lambda: next(readings)
        for step in range(4):
            clock.now += 10_000
            agent._traffic(clock.now)
            if step == 1:
                self.assertEqual(agent._bps, (800_000, 320_000))
            if step == 2:
                self.assertIsNone(agent._bps)
        self.assertEqual(agent._bps, (4_000, 1_600))

    def test_no_counters_leave_things_as_they_were(self):
        agent, io, clock = started()
        io.traffic = lambda: None
        before = agent._counters
        agent._traffic(clock.now)
        self.assertEqual(agent._counters, before)


if __name__ == "__main__":
    unittest.main()
