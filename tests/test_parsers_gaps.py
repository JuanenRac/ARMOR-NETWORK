"""The odd inputs of the text parsers: a route line that is not the default one, a node-status answer that stops early or has only group names, an address that is not one, and a service
type that is not a URN. Only text in, text out."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import parsers  # noqa: E402


def answer(names, pad=0):
    """A node-status answer with the given (name, flags) pairs."""
    head = struct.pack(">HHHHHH", 0x4152, 0x8400, 0, 1, 0, 0) + b"\x20" + b"CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + b"\x00"
    body = struct.pack(">HHIH", 0x0021, 1, 0, 1 + 18 * len(names)) + bytes([len(names)])
    for name, flags in names:
        body += name.encode().ljust(15, b" ") + b"\x00" + struct.pack(">H", flags)
    return head + body + b"\x00" * pad


class Routes(unittest.TestCase):
    def test_a_line_that_is_not_the_default_route_is_left_out(self):
        text = "10.0.0.0/24 dev eth0 proto kernel\ndefault via 192.168.0.1 dev eth0 metric 50"
        self.assertEqual(parsers.parse_ip_route(text), ("192.168.0.1", "eth0"))
        self.assertIsNone(parsers.parse_ip_route("10.0.0.0/24 dev eth0"))
        self.assertIsNone(parsers.parse_ip_route("default scope link"))

    def test_a_via_or_dev_that_ends_the_line_gives_nothing_for_that_part(self):
        self.assertEqual(parsers.parse_ip_route("default via"), (None, None))
        self.assertEqual(parsers.parse_ip_route("default dev"), (None, None))
        self.assertEqual(parsers.parse_ip_route("default via 10.0.0.1 dev eth0 metric"), ("10.0.0.1", "eth0"))

    def test_with_the_same_metric_the_first_route_is_kept(self):
        text = "default via 10.0.0.1 dev eth0\ndefault via 10.0.0.2 dev eth1"
        self.assertEqual(parsers.parse_ip_route(text), ("10.0.0.1", "eth0"))


class Ipconfig(unittest.TestCase):
    def test_the_zero_address_is_not_an_address_of_the_adapter(self):
        text = "Ethernet adapter Local:\n   IPv4 Address. . . : 0.0.0.0\n   Subnet Mask . . . : 255.255.255.0\n"
        adapters = parsers.parse_ipconfig(text)
        self.assertEqual(len(adapters), 1)
        self.assertEqual(adapters[0].masks, {})

    def test_a_mask_before_any_address_is_not_attached_to_anything(self):
        adapters = parsers.parse_ipconfig("Ethernet adapter Local:\n   Subnet Mask . . . : 255.255.255.0\n")
        self.assertEqual(adapters[0].masks, {})


class NetBios(unittest.TestCase):
    def test_the_first_unique_name_is_the_machine_and_group_names_are_skipped(self):
        self.assertEqual(parsers.parse_nbstat(answer([("WORKGROUP", 0x8000), ("JUANEN", 0)])), "JUANEN")

    def test_an_answer_with_only_group_names_or_a_blank_one_has_no_name(self):
        self.assertIsNone(parsers.parse_nbstat(answer([("WORKGROUP", 0x8000)] * 3)))
        self.assertIsNone(parsers.parse_nbstat(answer([("", 0)] * 3)))

    def test_an_answer_that_stops_before_its_names_is_none(self):
        full = answer([("JUANEN", 0)] * 3)
        self.assertIsNone(parsers.parse_nbstat(full[:70]))
        self.assertIsNone(parsers.parse_nbstat(full[:57]))
        self.assertEqual(parsers.parse_nbstat(full[:-5]), "JUANEN")   # the first name was whole
        groups = answer([("WORKGROUP", 0x8000)] * 3)
        self.assertIsNone(parsers.parse_nbstat(groups[:-5]))


class Services(unittest.TestCase):
    def test_a_service_type_that_is_not_a_urn_is_cut_and_an_empty_one_is_nothing(self):
        self.assertIsNone(parsers.ssdp_service("upnp:rootdevice"))
        self.assertEqual(parsers.ssdp_service("custom:thing"), "custom:thing")
        self.assertEqual(parsers.ssdp_service("x" * 80), "x" * 48)
        self.assertIsNone(parsers.ssdp_service(""))
        self.assertEqual(parsers.ssdp_service("urn:schemas-upnp-org:device:MediaServer:1"), "MediaServer")


if __name__ == "__main__":
    unittest.main()
