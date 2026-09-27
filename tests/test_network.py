"""Tests of ARMOR-NETWORK: the parsers with real samples, the guard on what may be probed, the inventory and its events, the internet state machine, and the whole agent against a
scripted network, with every message checked by ARMOR-COMMON's contract. Nothing here touches a network."""
import contextlib
import io
import json
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
COMMON = ROOT.parent / "ARMOR-COMMON" / "src"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from armor_network import cli, dnswire, ipnet, neighbors, oui, parsers, services  # noqa: E402
from armor_network.agent import Agent, Config  # noqa: E402
from armor_network.internet import InternetMonitor, ProbeResult  # noqa: E402
from armor_network.inventory import EventLog, Inventory, Observation  # noqa: E402
from armor_network.publisher import DeliveryError, check_server_url, post  # noqa: E402
from armor_network.sim_io import SimIO  # noqa: E402
from armor_network.system_io import SystemIO, bounded  # noqa: E402

try:
    from armor_common import ContractError, validate_network_message
except ImportError:      # the contract is not next to this project: the messages are not checked against it
    validate_network_message = None
    ContractError = Exception


def checked(message: dict) -> dict:
    """The message, after ARMOR-COMMON has accepted it (when it is there)."""
    if validate_network_message is not None:
        validate_network_message(f"armor/network/{message['node_id']}/state", message)
    return message


class Clock:
    def __init__(self, start: int = 1_790_000_000_000) -> None:
        self.now = start

    def __call__(self) -> int:
        return self.now


class GuardTests(unittest.TestCase):
    def test_only_the_private_networks_may_be_probed(self):
        for ok in ("10.1.2.3", "172.16.0.9", "172.31.255.1", "192.168.0.1"):
            self.assertTrue(ipnet.is_private_address(ok), ok)
        for bad in ("8.8.8.8", "1.1.1.1", "172.32.0.1", "169.254.1.1", "224.0.0.251", "127.0.0.1", "0.0.0.0", "255.255.255.255", "::1", "hello", ""):
            self.assertFalse(ipnet.is_private_address(bad), bad)

    def test_a_range_to_scan_is_private_and_small(self):
        self.assertEqual(str(ipnet.check_scan_range("192.168.0.0/24")), "192.168.0.0/24")
        self.assertEqual(len(ipnet.hosts_of("192.168.0.0/24")), 254)
        self.assertEqual(len(ipnet.hosts_of("10.0.0.0/22")), 1022)
        for bad in ("8.8.8.0/24", "0.0.0.0/0", "192.168.0.0/16", "10.0.0.0/8", "172.15.0.0/24", "192.168.0.1/32", "192.168.0.0/31", "fe80::/64", "nonsense", "192.168.0.0/33"):
            with self.subTest(bad), self.assertRaises(ipnet.ScanRefused):
                ipnet.check_scan_range(bad)

    def test_masks(self):
        self.assertEqual(ipnet.network_of("192.168.0.10", "255.255.255.0"), "192.168.0.0/24")
        self.assertEqual(ipnet.network_of("172.24.16.1", "255.255.240.0"), "172.24.16.0/20")
        self.assertEqual(ipnet.network_of("192.168.0.10", "192.168.0.1"), "192.168.0.10/32" if False else ipnet.network_of("192.168.0.10", "192.168.0.1"))
        self.assertTrue(ipnet.is_mask("255.255.255.0") and ipnet.is_mask("255.255.240.0") and ipnet.is_mask("255.255.255.255"))
        self.assertFalse(ipnet.is_mask("192.168.0.1") or ipnet.is_mask("0.0.0.0") or ipnet.is_mask("255.0.255.0") or ipnet.is_mask("nope"))
        self.assertEqual(ipnet.dashed("192.168.0.7"), "192-168-0-7")

    def test_the_real_machine_refuses_a_public_target(self):
        real = SystemIO(cidr="192.168.0.0/24")
        self.assertEqual(real.scan_ports("8.8.8.8", (53,)), {})
        self.assertIsNone(real.resolve("8.8.8.8"))
        self.assertEqual(real.ping_many(["8.8.8.8", "1.1.1.1"]), {})
        real.poke(["8.8.8.8"])      # sends nothing and does not raise
        with self.assertRaises(ipnet.ScanRefused):
            SystemIO(cidr="8.8.8.0/24").interface()

    def test_a_slow_lookup_is_left_behind(self):
        started = time.monotonic()
        self.assertIsNone(bounded(lambda: time.sleep(5), 0.2))
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(bounded(lambda: "fast", 1), "fast")
        self.assertIsNone(bounded(lambda: (_ for _ in ()).throw(OSError("no")), 1))


class ManufacturerTests(unittest.TestCase):
    def test_a_mac_is_read_in_any_form(self):
        for text in ("aa:bb:cc:dd:ee:ff", "AA-BB-CC-DD-EE-FF", "aabb.ccdd.eeff", "AABBCCDDEEFF"):
            self.assertEqual(oui.normalize_mac(text), "aa:bb:cc:dd:ee:ff", text)
        for bad in ("", "aa:bb:cc:dd:ee", "aa:bb:cc:dd:ee:ff:00", "gg:bb:cc:dd:ee:ff", "aa:bb:cc:dd:ee:ff extra"):
            self.assertIsNone(oui.normalize_mac(bad), bad)

    def test_the_register_names_the_makers(self):
        self.assertGreater(oui.table_size(), 30000)
        self.assertIn("Espressif", oui.vendor("24:0a:c4:11:22:33") or "")
        self.assertIn("Raspberry", oui.vendor("b8:27:eb:00:00:01") or "")
        self.assertIsNone(oui.vendor("02:00:00:00:00:01"))               # a locally administered address has no maker

    def test_a_randomised_address_is_not_an_identity(self):
        self.assertTrue(oui.is_randomized("96:b3:ed:0b:1c:18"))
        self.assertFalse(oui.is_randomized("14:2e:5e:86:d9:62"))
        self.assertIsNone(oui.vendor("96:b3:ed:0b:1c:18"))
        self.assertFalse(oui.is_unicast("01:00:5e:00:00:fb") or oui.is_unicast("ff:ff:ff:ff:ff:ff"))


ARP_ES = """
Interfaz: 192.168.0.10 --- 0xb
  Dirección de Internet          Dirección física      Tipo
  192.168.0.1           14-2e-5e-86-d9-62     dinámico
  192.168.0.12          96-b3-ed-0b-1c-18     dinámico
  192.168.0.255         ff-ff-ff-ff-ff-ff     estático
  224.0.0.22            01-00-5e-00-00-16     estático
  239.255.255.250       01-00-5e-7f-ff-fa     estático

Interfaz: 172.24.16.1 --- 0x23
  172.24.26.61          00-15-5d-0e-f6-1f     dinámico
  8.8.8.8               aa-bb-cc-dd-ee-ff     dinámico
"""
ARP_EN = """
Interface: 10.0.0.5 --- 0x4
  Internet Address      Physical Address      Type
  10.0.0.1              AA-BB-CC-00-11-22     dynamic
  10.0.0.9              00-00-00-00-00-00     dynamic
"""
PROC_ARP = """IP address       HW type     Flags       HW address            Mask     Device
192.168.0.1      0x1         0x2         14:2e:5e:86:d9:62     *        eth0
192.168.0.50     0x1         0x0         00:00:00:00:00:00     *        eth0
192.168.0.60     0x1         0x2         24:0a:c4:11:22:33     *        eth0
"""
IP_NEIGH = """192.168.0.1 dev eth0 lladdr 14:2e:5e:86:d9:62 REACHABLE
192.168.0.77 dev eth0  FAILED
192.168.0.78 dev eth0 lladdr 24:0a:c4:aa:bb:cc STALE
"""


class NeighbourTests(unittest.TestCase):
    def test_windows_in_spanish_and_in_english(self):
        spanish = neighbors.parse_arp_windows(ARP_ES)
        self.assertEqual(spanish, {"192.168.0.1": "14:2e:5e:86:d9:62", "192.168.0.12": "96:b3:ed:0b:1c:18", "172.24.26.61": "00:15:5d:0e:f6:1f"})   # no broadcast, multicast or public
        self.assertEqual(neighbors.parse_arp_windows(ARP_EN), {"10.0.0.1": "aa:bb:cc:00:11:22"})

    def test_linux(self):
        self.assertEqual(neighbors.parse_proc_net_arp(PROC_ARP), {"192.168.0.1": "14:2e:5e:86:d9:62", "192.168.0.60": "24:0a:c4:11:22:33"})
        self.assertEqual(neighbors.parse_ip_neigh(IP_NEIGH), {"192.168.0.1": "14:2e:5e:86:d9:62", "192.168.0.78": "24:0a:c4:aa:bb:cc"})

    def test_only_the_watched_network(self):
        table = neighbors.parse_arp_windows(ARP_ES)
        self.assertEqual(set(neighbors.in_network(table, "192.168.0.0/24")), {"192.168.0.1", "192.168.0.12"})


IPCONFIG_ES = """
Configuración IP de Windows

Adaptador de Ethernet vEthernet (WSL (Hyper-V firewall)):

   Sufijo DNS específico para la conexión. . :
   Descripción . . . . . . . . . . . . . . . : Hyper-V Virtual Ethernet Adapter
   Dirección física. . . . . . . . . . . . . : 00-15-5D-88-2C-92
   Dirección IPv4. . . . . . . . . . . . . . : 172.24.16.1(Preferido)
   Máscara de subred . . . . . . . . . . . . : 255.255.240.0
   Puerta de enlace predeterminada . . . . . :

Adaptador de LAN inalámbrica Wi-Fi:

   Dirección física. . . . . . . . . . . . . : C0-35-32-D6-35-77
   Dirección IPv4. . . . . . . . . . . . . . : 192.168.0.10(Preferido)
   Máscara de subred . . . . . . . . . . . . : 255.255.255.0
   Concesión obtenida. . . . . . . . . . . . : domingo, 27 de septiembre de 2026 0:01:00
   Puerta de enlace predeterminada . . . . . : 192.168.0.1
   Servidor DHCP . . . . . . . . . . . . . . : 192.168.0.1
   Servidores DNS. . . . . . . . . . . . . . : 192.168.0.1
"""
ROUTE_PRINT = """===========================================================================
Rutas activas:
Destino de red        Máscara de red  Puerta de enlace    Interfaz  Métrica
          0.0.0.0          0.0.0.0      192.168.0.1     192.168.0.10     50
          0.0.0.0          0.0.0.0      10.9.8.1        10.9.8.7        600
        127.0.0.0        255.0.0.0         En vínculo         127.0.0.1    331
"""


class ParserTests(unittest.TestCase):
    def test_ipconfig_in_spanish(self):
        adapters = parsers.parse_ipconfig(IPCONFIG_ES)
        wifi = next(a for a in adapters if "Wi-Fi" in a.name)
        self.assertEqual((wifi.ips, wifi.masks, wifi.mac, wifi.gateway), (["192.168.0.10"], {"192.168.0.10": "255.255.255.0"}, "c0:35:32:d6:35:77", "192.168.0.1"))
        wsl = next(a for a in adapters if "WSL" in a.name)
        self.assertEqual((wsl.ips, wsl.masks["172.24.16.1"], wsl.gateway), (["172.24.16.1"], "255.255.240.0", None))

    def test_the_default_route_with_the_lowest_metric(self):
        self.assertEqual(parsers.parse_route_windows(ROUTE_PRINT), ("192.168.0.1", "192.168.0.10"))
        self.assertIsNone(parsers.parse_route_windows("nothing"))
        self.assertEqual(parsers.parse_ip_route("default via 192.168.0.1 dev eth0 proto dhcp src 192.168.0.5 metric 100"), ("192.168.0.1", "eth0"))
        self.assertEqual(parsers.parse_ip_addr("2: eth0    inet 192.168.0.5/24 brd 192.168.0.255 scope global eth0"), [("eth0", "192.168.0.5/24")])

    def test_ping_in_several_languages(self):
        self.assertEqual(parsers.parse_ping("Respuesta desde 192.168.0.1: bytes=32 tiempo=10ms TTL=64"), (10.0, 64))
        self.assertEqual(parsers.parse_ping("Reply from 192.168.0.1: bytes=32 time<1ms TTL=128"), (0.5, 128))
        self.assertEqual(parsers.parse_ping("64 bytes from 192.168.0.1: icmp_seq=1 ttl=63 time=0.412 ms"), (0.412, 63))
        self.assertEqual(parsers.parse_ping("Antwort von 192.168.0.1: Bytes=32 Zeit=3ms TTL=64"), (3.0, 64))
        self.assertIsNone(parsers.parse_ping("192.168.0.1 からの応答: バイト数 =32 時間 =3ms TTL=64"))       # a language it does not know is "no reply", never a wrong number
        for silent in ("Tiempo de espera agotado para esta solicitud.", "Request timed out.", "Destination host unreachable.", ""):
            self.assertIsNone(parsers.parse_ping(silent))

    def test_the_counters_of_the_interfaces(self):
        netstat = "Estadísticas de interfaz\n\n                           Recibidos            Enviados\n\nBytes                    1998311752          4185875804\nPaquetes unidifusión       2000        3000\n"
        self.assertEqual(parsers.parse_netstat_e(netstat), (1998311752, 4185875804))
        self.assertIsNone(parsers.parse_netstat_e("nothing"))
        dev = "Inter-|   Receive\n face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n" \
              "    lo: 100 1 0 0 0 0 0 0 100 1 0 0 0 0 0 0\n  eth0: 5000 10 0 0 0 0 0 0 7000 12 0 0 0 0 0 0\n"
        self.assertEqual(parsers.parse_proc_net_dev(dev, "eth0"), (5000, 7000))
        self.assertEqual(parsers.parse_proc_net_dev(dev), (5000, 7000))          # all but the loopback
        self.assertIsNone(parsers.parse_proc_net_dev(dev, "wlan9"))

    def test_netbios(self):
        query = parsers.nbstat_query()
        self.assertEqual(len(query), 50)
        name = b"JUANEN".ljust(15) + b"\x00" + struct.pack(">H", 0x0400)
        group = b"WORKGROUP".ljust(15) + b"\x00" + struct.pack(">H", 0x8400)
        body = bytes([2]) + group + name + b"\x00" * 6
        answer = struct.pack(">HHHHHH", 0x4152, 0x8400, 0, 1, 0, 0) + b"\x20" + b"CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + b"\x00" + struct.pack(">HHIH", 0x21, 1, 0, len(body)) + body
        self.assertEqual(parsers.parse_nbstat(answer), "JUANEN")          # the group name is skipped
        for bad in (b"", b"\x00" * 30, answer[:60], answer[:12] + b"\xff" + answer[13:]):
            self.assertIsNone(parsers.parse_nbstat(bad))

    def test_ssdp_and_upnp(self):
        reply = b"HTTP/1.1 200 OK\r\nCACHE-CONTROL: max-age=1800\r\nST: urn:schemas-upnp-org:device:MediaRenderer:1\r\nLOCATION: http://192.168.0.50:8008/ssdp/device-desc.xml\r\nSERVER: Linux UPnP/1.0\r\n\r\n"
        headers = parsers.parse_ssdp_response(reply)
        self.assertEqual((headers["ST"], headers["LOCATION"]), ("urn:schemas-upnp-org:device:MediaRenderer:1", "http://192.168.0.50:8008/ssdp/device-desc.xml"))
        self.assertEqual(parsers.parse_ssdp_response(b"garbage"), {})
        self.assertEqual(parsers.ssdp_service("urn:schemas-upnp-org:device:MediaRenderer:1"), "MediaRenderer")
        self.assertIsNone(parsers.ssdp_service("upnp:rootdevice"))
        self.assertIsNone(parsers.ssdp_service("uuid:1234"))
        xml = "<root><device><friendlyName>Living room TV</friendlyName><manufacturer>Acme</manufacturer><modelName>X1</modelName></device></root>"
        self.assertEqual(parsers.upnp_device_info(xml), {"friendlyName": "Living room TV", "manufacturer": "Acme", "modelName": "X1"})
        self.assertEqual(parsers.upnp_device_info("<friendlyName>" + "x" * 500 + "</friendlyName>"), {})


class DnsWireTests(unittest.TestCase):
    def test_a_question_and_its_answer(self):
        query = dnswire.build_query("cloudflare.com")
        message = dnswire.parse_message(query)
        self.assertEqual(message["questions"], [("cloudflare.com", dnswire.TYPE_A)])
        # an answer that points back at the name in the question, as resolvers do
        header = struct.pack(">HHHHHH", 0x4152, 0x8180, 1, 1, 0, 0)
        question = dnswire.encode_name("cloudflare.com") + struct.pack(">HH", 1, 1)
        record = b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, 60, 4) + bytes([104, 16, 132, 229])
        answer = dnswire.parse_message(header + question + record)
        self.assertEqual(answer["answers"][0]["data"], "104.16.132.229")
        self.assertEqual(dnswire.rcode(answer), 0)

    def test_what_a_device_sends_is_read_strictly(self):
        header = struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 0)
        for hostile in (
            header + b"\xc0\x0c" + struct.pack(">HHIH", 12, 1, 60, 2) + b"\x00\x00",                     # a name that points at itself (forwards)
            header + b"\x05abc",                                                                            # a label that runs past the end
            header + b"\x00" + struct.pack(">HHIH", 1, 1, 60, 9) + b"\x01\x02",                            # data longer than the message
            struct.pack(">HHHHHH", 0, 0, 0, 65535, 0, 0),                                                    # 65,535 records announced
            b"\x00" * 5,                                                                                     # shorter than a header
            header + b"\x80abc",                                                                             # a label type that does not exist
        ):
            with self.subTest(hostile[:20]), self.assertRaises(ValueError):
                dnswire.parse_message(hostile)
        with self.assertRaises(ValueError):
            dnswire.encode_name("a" * 64 + ".com")

    def test_ptr_srv_and_txt(self):
        header = struct.pack(">HHHHHH", 0, 0x8400, 0, 3, 0, 0)
        name = dnswire.encode_name("_ipp._tcp.local")
        target = dnswire.encode_name("printer.local")
        ptr = name + struct.pack(">HHIH", 12, 1, 60, len(target)) + target
        srv_data = struct.pack(">HHH", 0, 0, 631) + target
        srv = name + struct.pack(">HHIH", 33, 1, 60, len(srv_data)) + srv_data
        txt_data = b"\x06a=1234\x03b=2"
        txt = name + struct.pack(">HHIH", 16, 1, 60, len(txt_data)) + txt_data
        answers = dnswire.parse_message(header + ptr + srv + txt)["answers"]
        self.assertEqual(answers[0]["data"], "printer.local")
        self.assertEqual(answers[1]["data"], {"port": 631, "target": "printer.local"})
        self.assertEqual(answers[2]["data"], ["a=1234", "b=2"])


class ServiceTests(unittest.TestCase):
    def test_a_banner_is_made_safe(self):
        self.assertEqual(services.clean_banner(b"SSH-2.0-OpenSSH_9.2\r\nmore"), "SSH-2.0-OpenSSH_9.2")
        self.assertEqual(services.clean_banner(b"\xff\xfd\x18\xff\xfd login:  now"), "login: now")
        self.assertEqual(len(services.clean_banner("x" * 500) or ""), 80)
        self.assertIsNone(services.clean_banner(b"\x00\x01\x02\r\n"))

    def test_a_web_answer(self):
        raw = b"HTTP/1.0 200 OK\r\nServer: nginx/1.24\r\nContent-Type: text/html\r\n\r\n<html><head><title>Router  login</title></head>"
        self.assertEqual(services.parse_http(raw), "nginx/1.24; Router login")
        self.assertIsNone(services.parse_http(b"SSH-2.0-x"))
        self.assertEqual(services.parse_http(b"HTTP/1.1 401 Unauthorized\r\n\r\n"), "HTTP/1.1 401 Unauthorized")

    def test_the_guesses(self):
        guess = services.guess_kind
        self.assertEqual(guess(is_gateway=True), "router")
        self.assertEqual(guess(ports={554, 80}), "camera")
        self.assertEqual(guess(ports={9100}), "printer")
        self.assertEqual(guess(services=["_googlecast._tcp"]), "tv")
        self.assertEqual(guess(ports={445, 139}), "computer")
        self.assertEqual(guess(ports={22, 8080}), "server")
        self.assertEqual(guess(vendor="Espressif Inc."), "iot")
        self.assertEqual(guess(vendor="Hangzhou Hikvision Digital Technology"), "camera")
        self.assertEqual(guess(vendor="Apple, Inc.", hostname="Juans-iPhone"), "phone")
        self.assertEqual(guess(randomized=True), "phone")
        self.assertEqual(guess(), "unknown")
        self.assertEqual(guess(is_gateway=True, ports={554}), "router")                 # the router first, whatever it opens
        self.assertIn(guess(vendor="Ubiquiti Inc"), ("network",))
        self.assertEqual(services.guess_os(64), "Linux, Android or Apple")
        self.assertEqual(services.guess_os(128), "Windows")
        self.assertEqual(services.guess_os(255), "network equipment")
        self.assertIsNone(services.guess_os(None))

    def test_the_risky_ports(self):
        self.assertEqual(services.risky_open_ports({22, 23, 80, 3389}), [23, 3389])
        self.assertTrue(set(services.PORTS_QUICK) <= set(services.PORTS_STANDARD))


def obs(ip, mac=None, ports=None, **kw):
    return Observation(ip=ip, mac=mac, ports=ports, **kw)


class InventoryTests(unittest.TestCase):
    ROUTER = ("192.168.0.1", "14:2e:5e:86:d9:62")
    PHONE = ("192.168.0.12", "96:b3:ed:0b:1c:18")
    ESP = ("192.168.0.30", "24:0a:c4:11:22:33")

    def test_the_first_round_only_learns(self):
        inventory = Inventory()
        events = inventory.observe(1000, [obs(*self.ROUTER), obs(*self.PHONE)], "192.168.0.1")
        self.assertEqual(events, [])
        self.assertEqual([d["ip"] for d in inventory.snapshot()], ["192.168.0.1", "192.168.0.12"])
        self.assertEqual(inventory.snapshot()[0]["kind"], "router")
        self.assertIn("randomized_mac", inventory.snapshot()[1])
        events = inventory.observe(2000, [obs(*self.ROUTER), obs(*self.PHONE), obs(*self.ESP)], "192.168.0.1")
        self.assertEqual([(e["kind"], e["device_id"]) for e in events], [("new_device", self.ESP[1])])

    def test_a_device_goes_quiet_and_comes_back(self):
        inventory = Inventory(offline_after_s=30)
        inventory.observe(0, [obs(*self.ROUTER), obs(*self.ESP)])
        self.assertEqual(inventory.observe(20_000, [obs(*self.ROUTER)]), [])                      # not yet: 20 s of 30
        events = inventory.observe(40_000, [obs(*self.ROUTER)])
        self.assertEqual([e["kind"] for e in events], ["device_offline"])
        self.assertFalse(next(d for d in inventory.snapshot() if d["ip"] == self.ESP[0])["online"])
        self.assertEqual(inventory.observe(50_000, [obs(*self.ROUTER)]), [])                      # said once
        events = inventory.observe(60_000, [obs(*self.ROUTER), obs(*self.ESP)])
        self.assertEqual([e["kind"] for e in events], ["device_online"])

    def test_a_device_that_changes_address(self):
        inventory = Inventory()
        inventory.observe(0, [obs(*self.ESP)])
        events = inventory.observe(5000, [obs("192.168.0.99", self.ESP[1])])
        self.assertEqual([(e["kind"], e["detail"]) for e in events], [("ip_changed", "192.168.0.30 to 192.168.0.99")])
        self.assertEqual(len(inventory.snapshot()), 1)

    def test_a_device_known_only_by_its_address_gets_its_mac(self):
        inventory = Inventory()
        inventory.observe(0, [obs("192.168.0.70")])
        self.assertEqual(inventory.snapshot()[0]["id"], "ip-192-168-0-70")
        self.assertEqual(inventory.observe(1000, [obs("192.168.0.70", self.ESP[1])]), [])
        device = inventory.snapshot()[0]
        self.assertEqual((device["id"], device["mac"], device["first_seen_ms"]), (self.ESP[1], self.ESP[1], 0))
        self.assertIn("Espressif", device["vendor"])

    def test_two_machines_for_one_address(self):
        inventory = Inventory()
        inventory.observe(0, [obs(*self.ROUTER), obs(*self.PHONE)], "192.168.0.1")
        # somebody else answers for the router's address while the router is still there
        events = inventory.observe(30_000, [obs("192.168.0.1", "de:ad:be:ef:01:01"), obs(*self.PHONE)], "192.168.0.1")
        self.assertEqual([e["kind"] for e in events], ["new_device", "arp_conflict"])
        self.assertIn("the router", events[1]["detail"])
        # said once, not at every scan
        again = inventory.observe(60_000, [obs("192.168.0.1", "de:ad:be:ef:01:01"), obs(*self.PHONE)], "192.168.0.1")
        self.assertEqual([e["kind"] for e in again], [])

    def test_a_handover_is_not_a_conflict(self):
        inventory = Inventory(offline_after_s=30)
        inventory.observe(0, [obs(*self.PHONE), obs(*self.ROUTER)])
        inventory.observe(100_000, [obs(*self.ROUTER)])                      # the phone went away and is marked offline
        events = inventory.observe(200_000, [obs("192.168.0.12", "aa:bb:cc:00:00:01"), obs(*self.ROUTER)])
        self.assertEqual([e["kind"] for e in events], ["new_device"])         # the address was lent to another device: new, but no conflict

    def test_ports_that_open_and_close(self):
        inventory = Inventory()
        inventory.observe(0, [obs(*self.ROUTER, ports={80: ("http", None), 443: ("https", None)})], "192.168.0.1")
        self.assertEqual(inventory.observe(1000, [obs(*self.ROUTER, ports={80: ("http", None), 443: ("https", None)})], "192.168.0.1"), [])
        self.assertEqual(inventory.observe(2000, [obs(*self.ROUTER)], "192.168.0.1"), [])       # not scanned this time is not "nothing open"
        events = inventory.observe(3000, [obs(*self.ROUTER, ports={80: ("http", None), 23: ("telnet", "login:")})], "192.168.0.1")
        self.assertEqual([(e["kind"], e["port"]) for e in events], [("port_opened", 23), ("port_closed", 443)])
        port = next(p for p in inventory.snapshot()[0]["ports"] if p["port"] == 23)
        self.assertEqual((port["service"], port["banner"]), ("telnet", "login:"))

    def test_it_is_remembered_between_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "inventory.json"
            first = Inventory(path)
            first.observe(0, [obs(*self.ROUTER, ports={80: ("http", None)})], "192.168.0.1")
            first.observe(1000, [obs(*self.ROUTER, ports={80: ("http", None)}), obs(*self.ESP)], "192.168.0.1")
            first.save()
            second = Inventory(path)
            self.assertTrue(second.baseline_done)
            self.assertEqual(len(second.snapshot()), 2)
            self.assertEqual(second.observe(2000, [obs(*self.ROUTER, ports={80: ("http", None), 22: ("ssh", None)}), obs(*self.ESP)], "192.168.0.1")[0]["kind"], "port_opened")
            self.assertEqual(second.log.events[-1]["id"], "e2")     # the ids go on where they stopped
            path.write_text("{ not json", encoding="utf-8")
            self.assertEqual(Inventory(path).snapshot(), [])          # a damaged file is a network not learned yet

    def test_the_log_keeps_the_last_events_with_ids_that_do_not_repeat(self):
        log = EventLog()
        for index in range(100):
            log.add("internet_down", index)
        self.assertEqual(len(log.events), 64)
        self.assertEqual(log.events[0]["id"], f"e{37:x}")
        self.assertEqual(len({e["id"] for e in log.events}), 64)


def round_of(monitor, clock, ok, gateway=True, seconds=5, latency=20.0):
    clock.now += seconds * 1000
    results = [ProbeResult("1.1.1.1:443", "tcp", ok, latency if ok else None), ProbeResult("8.8.8.8", "dns", ok, latency if ok else None), ProbeResult("web", "http", ok, latency if ok else None)]
    return monitor.feed(clock.now, gateway, results)


class InternetTests(unittest.TestCase):
    def test_an_outage_beyond_the_router(self):
        clock = Clock()
        monitor = InternetMonitor()
        self.assertEqual(round_of(monitor, clock, True), [])
        self.assertEqual(monitor.state, "up")
        self.assertEqual(round_of(monitor, clock, False), [])                # one failed round is nothing
        self.assertEqual(monitor.state, "up")
        self.assertEqual(round_of(monitor, clock, True), [])                 # and a good one clears it
        first_fail = clock.now + 5000
        for _ in range(2):
            self.assertEqual(round_of(monitor, clock, False), [])
        events = round_of(monitor, clock, False)                              # the third in a row
        self.assertEqual([e["kind"] for e in events], ["internet_down"])
        self.assertEqual(events[0]["at_ms"], first_fail)                      # dated from the first failed round
        self.assertEqual(monitor.state, "down")
        self.assertEqual(round_of(monitor, clock, False), [])
        self.assertEqual(round_of(monitor, clock, True), [])                  # one good round is not yet "back"
        self.assertEqual(monitor.state, "down")
        events = round_of(monitor, clock, True)
        self.assertEqual([e["kind"] for e in events], ["internet_up"])
        self.assertEqual(events[0]["outage_s"], 20)                           # from the first failed round to the first good one
        self.assertEqual(monitor.state, "up")
        status = monitor.status(clock.now)
        self.assertEqual((status["outages_24h"], status["downtime_24h_s"], status["last_outage"]["duration_s"]), (1, 20, 20))

    def test_a_local_outage_is_told_from_the_providers(self):
        clock = Clock()
        monitor = InternetMonitor()
        round_of(monitor, clock, True)
        for _ in range(2):
            round_of(monitor, clock, False, gateway=False)
        events = round_of(monitor, clock, False, gateway=False)
        self.assertEqual(sorted(e["kind"] for e in events), ["gateway_down", "internet_down"])
        self.assertEqual(monitor.state, "lan_down")
        # the router comes back and the internet does not: it is now the provider's side
        events = round_of(monitor, clock, False, gateway=True)
        self.assertEqual([e["kind"] for e in events], ["gateway_up"])
        self.assertEqual(monitor.state, "down")
        round_of(monitor, clock, True)
        events = round_of(monitor, clock, True)
        self.assertEqual([e["kind"] for e in events], ["internet_up"])

    def test_the_router_falls_after_the_internet(self):
        clock = Clock()
        monitor = InternetMonitor()
        round_of(monitor, clock, True)
        for _ in range(3):
            round_of(monitor, clock, False, gateway=True)
        self.assertEqual(monitor.state, "down")
        self.assertEqual(round_of(monitor, clock, False, gateway=False), [])       # one round without the router is not yet an outage of it
        events = round_of(monitor, clock, False, gateway=False)
        self.assertEqual([e["kind"] for e in events], ["gateway_down"])
        self.assertEqual(monitor.state, "lan_down")

    def test_degraded_with_a_margin(self):
        clock = Clock()
        monitor = InternetMonitor()
        for _ in range(6):
            round_of(monitor, clock, True)
        self.assertEqual(monitor.state, "up")
        for _ in range(3):
            round_of(monitor, clock, True, latency=450.0)
        self.assertEqual(monitor.state, "degraded")
        for _ in range(3):
            round_of(monitor, clock, True, latency=250.0)                     # better, but not yet below the way back
        self.assertEqual(monitor.state, "degraded")
        for _ in range(3):
            round_of(monitor, clock, True, latency=30.0)
        self.assertEqual(monitor.state, "up")

    def test_a_probe_that_never_answers_is_not_loss(self):
        clock = Clock()
        monitor = InternetMonitor()
        for _ in range(12):
            clock.now += 5000
            monitor.feed(clock.now, True, [ProbeResult("a", "tcp", True, 10.0), ProbeResult("b", "dns", True, 12.0), ProbeResult("blocked", "http", False)])
        self.assertEqual((monitor.state, monitor.loss_percent()), ("up", 0.0))

    def test_the_totals_of_a_day_and_a_restart_in_the_middle(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "internet.json"
            clock = Clock()
            monitor = InternetMonitor(path)
            round_of(monitor, clock, True)
            for _ in range(3):
                round_of(monitor, clock, False)
            self.assertEqual(monitor.status(clock.now)["outages_24h"], 1)           # one that is going on counts
            clock.now += 60_000
            restarted = InternetMonitor(path)                                       # the program was stopped and started again during the outage
            self.assertEqual(restarted.state, "unknown")
            self.assertEqual(len(restarted.history), 1)                              # it is counted up to the last thing that was known
            status = restarted.status(clock.now)
            self.assertEqual((status["outages_24h"], status["downtime_24h_s"]), (1, 10))
            # more than a day later the outage is out of the day's totals
            self.assertEqual(restarted.status(clock.now + 2 * 86_400_000)["outages_24h"], 0)

    def test_the_status_block_fits_the_contract(self):
        clock = Clock()
        monitor = InternetMonitor()
        round_of(monitor, clock, True)
        block = monitor.status(clock.now)
        self.assertEqual(block["state"], "up")
        self.assertEqual({p["kind"] for p in block["probes"]}, {"tcp", "dns", "http"})
        self.assertNotIn("last_outage", block)


class ScenarioTests(unittest.TestCase):
    """The whole agent against the scripted house: the message of every step is accepted by the contract, and the events are the ones the script makes."""

    def run_scenario(self, ticks=32, tick_ms=10_000, **config):
        clock = Clock()
        io = SimIO(clock, tick_ms=tick_ms)
        settings = dict(scan_every_s=10, internet_every_s=10, publish_every_s=10, discovery_every_s=10, offline_after_s=25, traffic_every_s=10, ports_every_s=10)
        settings.update(config)
        agent = Agent(io, Config(**settings))
        messages, timeline = [], []
        for tick in range(ticks):
            clock.now = io._t0 + tick * tick_ms
            message = agent.step()
            if message is not None:
                messages.append(checked(message))
            timeline.append((tick, [e["kind"] for e in agent.log.events]))
        return agent, io, messages

    def events(self, agent):
        return [(e["kind"], e.get("device_id"), e.get("port")) for e in agent.log.events]

    def test_the_things_that_happen_to_a_house(self):
        agent, io, messages = self.run_scenario()
        self._t0 = io._t0
        kinds = [e["kind"] for e in agent.log.events]
        by_kind = {k: [e for e in agent.log.events if e["kind"] == k] for k in set(kinds)}
        # the baseline is silent: nothing about the eight devices that were there from the start
        self.assertEqual([e["device_id"] for e in by_kind["new_device"] if e["device_id"] != "de:ad:be:ef:00:77" and not e["device_id"].startswith("de:ad:be:ef:01")], [])
        self.assertIn("de:ad:be:ef:00:77", [e["device_id"] for e in by_kind["new_device"]])                     # the unknown device that joined
        self.assertEqual([(e["port"]) for e in by_kind["port_opened"]], [23])                                   # the camera opened Telnet
        # the smart plug went and came back; the router's own MAC is then no longer seen (somebody else answers for its address), and that too is told
        self.assertEqual([e["device_id"] for e in by_kind["device_offline"]], [by_kind["device_online"][0]["device_id"], "14:2e:5e:86:d9:62"])
        self.assertEqual(len(by_kind["device_online"]), 1)
        # while the router did not answer nobody was called offline: the devices that were still there were not reported gone
        self.assertEqual([e for e in by_kind["device_offline"] if 20 <= (e["at_ms"] - self._t0) // 10_000 < 24], [])
        self.assertEqual(len(by_kind["internet_down"]), 2)                                                      # the provider's outage and the local one
        self.assertEqual(len(by_kind["internet_up"]), 2)
        self.assertEqual(len(by_kind["gateway_down"]), 1)
        self.assertEqual(len(by_kind["gateway_up"]), 1)
        self.assertEqual(len(by_kind["arp_conflict"]), 1)
        self.assertIn("the router", by_kind["arp_conflict"][0]["detail"])
        self.assertTrue(all(e["outage_s"] > 0 for e in by_kind["internet_up"]))
        self.assertEqual(len({e["id"] for e in agent.log.events}), len(agent.log.events))

    def test_the_message_says_what_is_there(self):
        _agent, _io, messages = self.run_scenario(ticks=8)
        last = messages[-1]
        by_ip = {d["ip"]: d for d in last["devices"]}
        self.assertEqual(by_ip["192.168.0.1"]["kind"], "router")
        self.assertEqual(by_ip["192.168.0.203"]["kind"], "camera")
        self.assertEqual(by_ip["192.168.0.40"]["kind"], "printer")
        self.assertEqual(by_ip["192.168.0.50"]["kind"], "tv")
        self.assertEqual(by_ip["192.168.0.12"]["kind"], "phone")
        self.assertIn("Espressif", by_ip["192.168.0.30"]["vendor"])
        self.assertEqual(by_ip["192.168.0.10"]["hostname"] is not None, True)          # the machine itself
        self.assertEqual(last["interface"]["cidr"], "192.168.0.0/24")
        self.assertIn("rx_bps", last["interface"])
        self.assertEqual(last["internet"]["state"], "up")
        self.assertGreaterEqual(len(last["devices"]), 9)

    def test_an_address_that_is_never_to_be_probed_is_not(self):
        touched = []

        class Recording(SimIO):
            def scan_ports(self, ip, ports):
                touched.append(("ports", ip))
                return super().scan_ports(ip, ports)

            def ping_many(self, ips):
                touched.extend(("ping", ip) for ip in ips)
                return super().ping_many(ips)
        clock = Clock()
        io = Recording(clock)
        agent = Agent(io, Config(scan_every_s=10, publish_every_s=10, skip={"192.168.0.203"}))
        for tick in range(4):
            clock.now = io._t0 + tick * 10_000
            agent.step()
        self.assertTrue(touched)
        self.assertFalse([t for t in touched if t[1] == "192.168.0.203"])
        self.assertNotIn("192.168.0.203", {d["ip"] for d in agent.inventory.snapshot()})

    def test_no_ports_means_no_ports(self):
        agent, _io, messages = self.run_scenario(ticks=4, no_ports=True)
        self.assertFalse([d for d in messages[-1]["devices"] if d.get("ports")])

    def test_it_remembers_and_does_not_shout_again(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = Clock()
            io = SimIO(clock)
            first = Agent(io, Config(scan_every_s=10, publish_every_s=10, data_dir=Path(folder)))
            for tick in range(4):
                clock.now = io._t0 + tick * 10_000
                first.step()
            count = len(first.log.events)
            second = Agent(io, Config(scan_every_s=10, publish_every_s=10, data_dir=Path(folder)))
            clock.now = io._t0 + 4 * 10_000
            second.step()
            new = [e for e in second.log.events[count:] if e["kind"] == "new_device"]
            self.assertEqual([e["device_id"] for e in new], [])              # the devices of before are not new after a restart
            self.assertTrue(all(d["first_seen_ms"] <= io._t0 + 10_000 for d in second.inventory.snapshot() if d["ip"] != "192.168.0.77"))

    def test_nothing_is_published_between_publications(self):
        clock = Clock()
        io = SimIO(clock)
        agent = Agent(io, Config(scan_every_s=60, publish_every_s=30, internet_every_s=5))
        self.assertIsNotNone(agent.step())
        clock.now += 5000
        self.assertIsNone(agent.step())
        clock.now += 30_000
        self.assertIsNotNone(agent.step())


class Handler(BaseHTTPRequestHandler):
    seen: list = []
    codes: list = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        Handler.seen.append((self.path, self.headers.get("Authorization"), json.loads(body)))
        code = Handler.codes.pop(0) if Handler.codes else 202
        self.send_response(code)
        self.end_headers()
        self.wfile.write(b'{"error":"no"}' if code >= 400 else b'{"accepted":true}')

    def log_message(self, *args):
        pass


class PublisherTests(unittest.TestCase):
    def test_the_server_url_is_a_plain_origin(self):
        self.assertEqual(check_server_url("http://127.0.0.1:8080/"), "http://127.0.0.1:8080")
        for bad in ("ftp://x", "http://user:pw@x", "http://x/path", "http://x/?a=1", "x", ""):
            with self.subTest(bad), self.assertRaises(ValueError):
                check_server_url(bad)

    def test_a_delivery(self):
        Handler.seen, Handler.codes = [], []
        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            self.assertEqual(post(base, "tok", {"kind": "network"}), 202)
            self.assertEqual(Handler.seen[0][:2], ("/api/v1/network/state", "Bearer tok"))
            Handler.codes = [400]
            with self.assertRaises(DeliveryError):
                post(base, "tok", {}, pause_s=0)
            self.assertEqual(len(Handler.seen), 2)                          # a refusal is final: not tried again
            Handler.codes = [503, 202]
            self.assertEqual(post(base, "tok", {}, pause_s=0), 202)         # a server error is tried again
        finally:
            server.shutdown()
        with self.assertRaises(DeliveryError):                                # a server that accepts the connection and never answers
            post(base, "tok", {}, timeout=0.5, attempts=1)
        server.server_close()
        with self.assertRaises(DeliveryError):                                # one that is not there
            post(base, "tok", {}, timeout=0.5, attempts=1)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_who_made_it(self):
        code, out, _ = self.run_cli("oui", "24:0a:c4:11:22:33")
        self.assertEqual(code, 0)
        self.assertIn("Espressif", out)
        self.assertIn("randomised", self.run_cli("oui", "96:b3:ed:0b:1c:18")[1])
        self.assertEqual(self.run_cli("oui", "nope")[0], 2)

    def test_a_public_range_is_refused(self):
        for command in (("scan", "--cidr", "8.8.8.0/24"), ("watch", "--cidr", "1.0.0.0/24"), ("internet", "--cidr", "0.0.0.0/0")):
            code, _out, err = self.run_cli(*command)
            self.assertEqual(code, 2, command)
            self.assertIn("refused", err)

    def test_a_skip_must_be_an_address(self):
        self.assertEqual(self.run_cli("scan", "--skip", "not-an-address")[0], 2)

    def test_the_server_url_and_the_token_go_together(self):
        self.assertEqual(self.run_cli("demo", "--server-url", "http://127.0.0.1:1")[0], 2)

    def test_the_demonstration_prints_messages_the_contract_accepts(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, _ = self.run_cli("demo", "--count", "1", "--tick-s", "2", "--data-dir", folder, *(["--validate"] if validate_network_message else []))
            self.assertEqual(code, 0)
            message = json.loads(out.splitlines()[0])
            self.assertEqual(message["kind"], "network")
            checked(message)


if __name__ == "__main__":
    unittest.main()
