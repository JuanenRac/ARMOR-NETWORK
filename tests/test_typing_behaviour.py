"""The behaviour the type annotations of the scan guard, the order parser and the vendor tables must keep: these were written down before the types were tightened."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import ipnet, services  # noqa: E402
from armor_network.orders import parse_orders  # noqa: E402


class ScanGuard(unittest.TestCase):
    def test_ipv6_and_public_ranges_are_refused(self):
        for bad in ("fe80::/64", "2001:db8::/32", "8.8.8.0/24", "172.32.0.0/24"):
            with self.assertRaises(ipnet.ScanRefused):
                ipnet.check_scan_range(bad)

    def test_private_range_edges(self):
        self.assertEqual(str(ipnet.check_scan_range("172.16.5.0/24")), "172.16.5.0/24")
        self.assertEqual(str(ipnet.check_scan_range("10.1.2.3/30")), "10.1.2.0/30")
        with self.assertRaises(ipnet.ScanRefused):
            ipnet.check_scan_range("10.0.0.0/21")
        with self.assertRaises(ipnet.ScanRefused):
            ipnet.check_scan_range("10.0.0.0/31")


class OrderParsing(unittest.TestCase):
    def _order(self, **extra):
        return parse_orders({"commands": [{"type": "inspect", "id": "abc12345", "ip": "192.168.0.9", **extra}]})

    def test_login_only_for_inspect_with_a_dict(self):
        order = self._order(auth={"user": "admin", "password": "pw"})[0]
        self.assertEqual((order.user, order.password), ("admin", "pw"))
        self.assertEqual(self._order(auth="admin")[0].user, None)
        wake = parse_orders({"commands": [{"type": "wake", "id": "abc12345", "mac": "AA:BB:CC:DD:EE:FF", "auth": {"user": "x", "password": "y"}}]})[0]
        self.assertEqual((wake.user, wake.password, wake.mac), (None, None, "aa:bb:cc:dd:ee:ff"))

    def test_login_with_a_wrong_shape_is_dropped(self):
        order = self._order(auth={"user": "u" * 65, "password": "pw"})[0]
        self.assertEqual((order.user, order.password), (None, None))


class KindTables(unittest.TestCase):
    def test_vendor_kinds(self):
        for vendor, kind in (("Hikvision Digital", "camera"), ("Brother Industries", "printer"), ("Synology Inc", "nas"), ("Espressif Inc", "iot"), ("Ubiquiti Networks", "network"),
                             ("Raspberry Pi Trading", "computer")):
            self.assertEqual(services.guess_kind(vendor=vendor), kind, vendor)

    def test_name_and_service_kinds(self):
        self.assertEqual(services.guess_kind(hostname="living-room-tv"), "tv")
        self.assertEqual(services.guess_kind(services=["_ipp._tcp"]), "printer")


if __name__ == "__main__":
    unittest.main()
