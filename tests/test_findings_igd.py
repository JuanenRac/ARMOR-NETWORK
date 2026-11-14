"""The findings of the network (risky ports, a second DHCP server) and the read-only questions to the router: packets and answers built and read without a socket."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import findings, igd, rogue_dhcp  # noqa: E402
from armor_network.services import RISKY_PORTS  # noqa: E402

MAC = bytes([2, 0, 0, 0, 0, 1])


def offer(xid: int, server: str = "192.168.1.1", offered: str = "192.168.1.50", extra: bytes = b"") -> bytes:
    def ip(text: str) -> bytes:
        return bytes(int(part) for part in text.split("."))
    header = struct.pack("!BBBBIHH4s4s4s4s16s64s128s", 2, 1, 6, 0, xid, 0, 0x8000, b"\0" * 4, ip(offered), b"\0" * 4, b"\0" * 4, MAC + b"\0" * 10, b"\0" * 64, b"\0" * 128)
    options = bytes([53, 1, 2, 54, 4]) + ip(server) + bytes([3, 4]) + ip(server) + bytes([6, 8]) + ip("8.8.8.8") + ip("1.1.1.1") + bytes([51, 4]) + struct.pack("!I", 3600)
    return header + rogue_dhcp.MAGIC_COOKIE + options + extra + bytes([255])


class Dhcp(unittest.TestCase):
    def test_the_question_is_a_discover_with_the_broadcast_flag_and_our_transaction(self):
        packet = rogue_dhcp.build_discover(MAC, 0xAABBCCDD)
        self.assertEqual(packet[0], 1)
        self.assertEqual(packet[4:8], bytes.fromhex("aabbccdd"))
        self.assertEqual(packet[10:12], b"\x80\x00")
        self.assertEqual(packet[28:34], MAC)
        self.assertEqual(packet[236:240], rogue_dhcp.MAGIC_COOKIE)
        self.assertEqual(packet[240:243], bytes([53, 1, 1]))
        with self.assertRaises(ValueError):
            rogue_dhcp.build_discover(b"123", 1)
        with self.assertRaises(ValueError):
            rogue_dhcp.build_discover(MAC, 2 ** 32)

    def test_an_offer_to_us_is_read_and_one_to_somebody_else_is_not(self):
        reading = rogue_dhcp.parse_offer(offer(7), 7)
        self.assertEqual(reading, {"server": "192.168.1.1", "offered": "192.168.1.50", "router": "192.168.1.1", "dns": ["8.8.8.8", "1.1.1.1"], "lease_s": 3600})
        self.assertIsNone(rogue_dhcp.parse_offer(offer(7), 8))

    def test_what_is_not_a_well_formed_offer_is_none_not_a_crash(self):
        good = offer(7)
        for bad in (b"", good[:100], good[:239], b"\x01" + good[1:], good[:236] + b"abcd" + good[240:], good[:-1][:243] + b"\x35", good[:241] + bytes([5]),
                    good.replace(bytes([53, 1, 2]), bytes([53, 1, 5]), 1), good.replace(bytes([54, 4]), bytes([54, 3]), 1)):
            self.assertIsNone(rogue_dhcp.parse_offer(bad, 7), bad[:20])

    def test_only_a_server_that_is_not_allowed_is_a_finding_and_each_once(self):
        offers = [{"server": "192.168.1.1", "offered": "192.168.1.50"}, {"server": "192.168.1.77", "offered": "192.168.1.60", "router": "192.168.1.77"},
                  {"server": "192.168.1.77", "offered": "192.168.1.61"}, {"offered": "x"}]
        result = rogue_dhcp.judge(offers, {"192.168.1.1"})
        self.assertEqual(result, [{"kind": "rogue_dhcp", "server": "192.168.1.77", "offered": "192.168.1.60", "router": "192.168.1.77"}])
        self.assertEqual(rogue_dhcp.judge(offers, {"192.168.1.1", "192.168.1.77"}), [])
        self.assertEqual(rogue_dhcp.judge([], set()), [])


class Findings(unittest.TestCase):
    def test_every_risky_port_has_a_recommendation_and_a_stable_id(self):
        devices = [{"id": "nas", "ports": [{"port": 445, "service": "smb"}, {"port": 80}, {"port": 23}]}, {"id": "cam", "ports": [{"port": 554}]}]
        result = findings.risky_port_findings(devices)
        self.assertEqual([item["id"] for item in result], ["risky_port:nas:23", "risky_port:nas:445"])
        self.assertEqual(result[0]["recommendation"], "close_telnet")
        self.assertEqual(result, findings.risky_port_findings(devices), "the same network gives the same findings")
        self.assertEqual(set(findings.RECOMMENDATIONS), set(RISKY_PORTS))

    def test_a_device_with_odd_data_gives_no_finding_instead_of_an_error(self):
        self.assertEqual(findings.risky_port_findings([{"id": 5, "ports": [{"port": 23}]}, {"id": "a", "ports": "23"}, {"id": "b", "ports": [{"port": True}, {"port": "23"}, None]}, {}]), [])

    def test_the_two_kinds_are_joined_and_limited(self):
        rogue = [{"kind": "rogue_dhcp", "server": "192.168.1.77", "offered": "192.168.1.60"}]
        result = findings.all_findings([{"id": "nas", "ports": [{"port": 23}]}], rogue)
        self.assertEqual([item["kind"] for item in result], ["risky_port", "rogue_dhcp"])
        many = [{"id": f"d{index}", "ports": [{"port": 23}]} for index in range(200)]
        self.assertEqual(len(findings.all_findings(many, rogue)), findings.MAX_FINDINGS)


DESCRIPTION = ("<root><device><serviceList><service><serviceType>urn:schemas-upnp-org:service:Layer3Forwarding:1</serviceType><controlURL>/l3</controlURL></service>"
               "<service><serviceType>urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1</serviceType><controlURL>/ctl/CmnIfCfg</controlURL></service></serviceList></device></root>")


class Igd(unittest.TestCase):
    def test_the_control_address_is_the_one_of_the_right_service_on_the_same_local_host(self):
        self.assertEqual(igd.control_url(DESCRIPTION, "http://192.168.1.1:5000/rootDesc.xml"), "http://192.168.1.1:5000/ctl/CmnIfCfg")
        self.assertIsNone(igd.control_url(DESCRIPTION.replace("WANCommonInterfaceConfig", "Other"), "http://192.168.1.1:5000/d.xml"))
        self.assertIsNone(igd.control_url(DESCRIPTION, "http://8.8.8.8/d.xml"), "only a private address is ever asked")
        elsewhere = DESCRIPTION.replace("/ctl/CmnIfCfg", "http://192.168.1.99/ctl")
        self.assertIsNone(igd.control_url(elsewhere, "http://192.168.1.1/d.xml"), "a description cannot send the question to another host")

    def test_only_the_two_read_only_actions_can_be_built(self):
        self.assertIn(b"GetTotalBytesReceived", igd.soap_body("GetTotalBytesReceived"))
        self.assertEqual(igd.soap_headers("GetTotalBytesSent")["SOAPAction"], '"urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1#GetTotalBytesSent"')
        for action in ("AddPortMapping", "SetConnectionType", ""):
            with self.assertRaises(ValueError):
                igd.soap_body(action)
            with self.assertRaises(ValueError):
                igd.soap_headers(action)

    def test_a_counter_is_a_plain_unsigned_number_or_nothing(self):
        text = "<u:GetTotalBytesReceivedResponse><NewTotalBytesReceived>123456</NewTotalBytesReceived></u:GetTotalBytesReceivedResponse>"
        self.assertEqual(igd.parse_counter("GetTotalBytesReceived", text), 123456)
        for bad in ("", "<NewTotalBytesReceived>-5</NewTotalBytesReceived>", "<NewTotalBytesReceived>1e9</NewTotalBytesReceived>", "<NewTotalBytesReceived>" + "9" * 21 + "</NewTotalBytesReceived>",
                    "<NewTotalBytesSent>5</NewTotalBytesSent>"):
            self.assertIsNone(igd.parse_counter("GetTotalBytesReceived", bad), bad)
        self.assertIsNone(igd.parse_counter("Other", text))

    def test_the_totals_need_both_answers(self):
        answers = {"GetTotalBytesReceived": "<NewTotalBytesReceived>10</NewTotalBytesReceived>", "GetTotalBytesSent": "<NewTotalBytesSent>4</NewTotalBytesSent>"}

        def ask(url, body, headers):
            return answers[headers["SOAPAction"].split("#")[1].strip('"')]

        self.assertEqual(igd.read_totals("http://192.168.1.1/ctl", ask), (10, 4))
        answers["GetTotalBytesSent"] = "garbage"
        self.assertIsNone(igd.read_totals("http://192.168.1.1/ctl", ask))
        self.assertIsNone(igd.read_totals("http://192.168.1.1/ctl", lambda *_: None))

    def test_a_rate_needs_two_readings_and_a_counter_that_goes_down_restarts_the_measure(self):
        meter = igd.RateMeter()
        self.assertIsNone(meter.update(0.0, 1000, 500))
        self.assertEqual(meter.update(10.0, 3000, 1500), (200.0, 100.0))
        self.assertIsNone(meter.update(20.0, 100, 50), "the router restarted")
        self.assertEqual(meter.update(30.0, 1100, 250), (100.0, 20.0))
        self.assertIsNone(meter.update(30.0, 1200, 300), "no time passed")


if __name__ == "__main__":
    unittest.main()
