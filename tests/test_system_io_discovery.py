"""What devices announce about themselves (mDNS and SSDP), read through a stand-in UDP socket: which answers are kept, which are ignored and what is never believed.
Nothing here sends a packet; the clock and the socket are replaced.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later."""
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import dnswire, system_io  # noqa: E402
from armor_network.system_io import SystemIO  # noqa: E402

SSDP = (b"HTTP/1.1 200 OK\r\nST: urn:schemas-upnp-org:device:MediaRenderer:1\r\nLOCATION: http://192.168.0.20:49152/desc.xml\r\nSERVER: tv\r\n\r\n")


class FakeUdp:
    """A socket that answers `incoming` one by one (an exception in the list is raised) and records what is sent; sending to the addresses in `refuse` fails."""

    def __init__(self, incoming, refuse=()):
        self.incoming, self.sent, self.closed, self.refuse = list(incoming), [], False, set(refuse)
        self.options = []

    def settimeout(self, value):
        pass

    def setsockopt(self, *args):
        self.options.append(args)

    def sendto(self, data, address):
        if address[0] in self.refuse:
            raise OSError("network is unreachable")
        self.sent.append((data, address))

    def recvfrom(self, size):
        item = self.incoming.pop(0) if self.incoming else socket.timeout()
        if isinstance(item, BaseException):
            raise item
        return item

    def close(self):
        self.closed = True


def answers(*items):
    return {"answers": [{"type": kind, "name": name, "data": data} for kind, name, data in items]}


class Clock:
    """monotonic() that moves one step at each call, so a listening window of N steps reads N times."""

    def __init__(self, steps):
        self.now, self.steps = 0.0, steps

    def __call__(self):
        self.now += 1.0
        return self.now


def discover(sock, parse=None, clock_steps=40, listen_s=30, open_url=None):
    patches = [mock.patch.object(system_io.socket, "socket", return_value=sock), mock.patch.object(system_io.time, "monotonic", Clock(clock_steps))]
    if parse is not None:
        patches.append(mock.patch.object(system_io.dnswire, "parse_message", parse))
    if open_url is not None:
        patches.append(mock.patch.object(system_io, "_open", open_url))
    for patch in patches:
        patch.start()
    try:
        return SystemIO().discover(listen_s=listen_s)
    finally:
        for patch in reversed(patches):
            patch.stop()


class Discovery(unittest.TestCase):
    def test_the_two_questions_are_multicast_and_the_socket_is_always_closed(self):
        sock = FakeUdp([])
        self.assertEqual(discover(sock, listen_s=1), {})
        destinations = [address for _, address in sock.sent]
        self.assertEqual(destinations, [("224.0.0.251", 5353), ("239.255.255.250", 1900)])
        self.assertIn(b"M-SEARCH", sock.sent[1][0])
        self.assertTrue(sock.closed)

    def test_a_network_that_cannot_send_gives_nothing_and_still_closes_the_socket(self):
        sock = FakeUdp([], refuse={"224.0.0.251"})
        self.assertEqual(discover(sock), {})
        self.assertTrue(sock.closed)

    def test_an_mdns_answer_names_the_services_and_the_host_of_that_address_only(self):
        message = answers((dnswire.TYPE_PTR, "x", "_http._tcp.local"), (dnswire.TYPE_PTR, "x", "_http._tcp.local"), (dnswire.TYPE_PTR, "x", "_ipp._tcp.local"),
                          (dnswire.TYPE_A, "printer.local", "192.168.0.30"), (dnswire.TYPE_A, "liar.local", "192.168.0.99"))
        found = discover(FakeUdp([(b"mdns", ("192.168.0.30", 5353)), socket.timeout()]), parse=lambda data: message, clock_steps=6, listen_s=2)
        self.assertEqual(found, {"192.168.0.30": {"hostname": "printer", "services": ["_http._tcp", "_ipp._tcp"]}})

    def test_an_answer_from_outside_the_private_ranges_is_ignored(self):
        message = answers((dnswire.TYPE_PTR, "x", "_http._tcp.local"))
        found = discover(FakeUdp([(b"mdns", ("8.8.8.8", 5353))]), parse=lambda data: message, clock_steps=4, listen_s=1)
        self.assertEqual(found, {})

    def test_a_message_that_cannot_be_read_is_skipped_and_the_listening_goes_on(self):
        def parse(data):
            raise ValueError("garbage")
        found = discover(FakeUdp([(b"junk", ("192.168.0.30", 5353)), OSError("reset")]), parse=parse, clock_steps=6, listen_s=2)
        self.assertEqual(found, {})

    def test_an_ssdp_answer_gives_the_service_and_the_description_names_the_device(self):
        class Description:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size):
                return b"<root><device><friendlyName>Living room TV</friendlyName></device></root>"
        asked = []

        def open_url(location, *args):
            asked.append(location)
            return Description()
        found = discover(FakeUdp([(SSDP, ("192.168.0.20", 1900))]), clock_steps=8, listen_s=3, open_url=open_url)
        self.assertEqual(found["192.168.0.20"]["hostname"], "Living room TV")
        self.assertEqual(len(found["192.168.0.20"]["services"]), 1)
        self.assertEqual(asked, ["http://192.168.0.20:49152/desc.xml"])

    def test_a_location_on_another_address_is_never_fetched(self):
        liar = SSDP.replace(b"192.168.0.20:49152", b"192.168.0.77:80")
        asked = []
        found = discover(FakeUdp([(liar, ("192.168.0.20", 1900))]), clock_steps=8, listen_s=3, open_url=lambda *args: asked.append(args))
        self.assertEqual(asked, [])
        self.assertIsNone(found["192.168.0.20"]["hostname"])

    def test_a_description_that_cannot_be_fetched_leaves_the_host_unnamed(self):
        def broken(*args):
            raise OSError("refused")
        found = discover(FakeUdp([(SSDP, ("192.168.0.20", 1900))]), clock_steps=8, listen_s=3, open_url=broken)
        self.assertIsNone(found["192.168.0.20"]["hostname"])

    def test_a_name_the_device_already_gave_by_mdns_is_not_replaced_by_its_description(self):
        message = answers((dnswire.TYPE_A, "tv.local", "192.168.0.20"))

        class Description:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size):
                return b"<friendlyName>Another name</friendlyName>"
        found = discover(FakeUdp([(b"mdns", ("192.168.0.20", 5353)), (SSDP, ("192.168.0.20", 1900))]), parse=lambda data: message, clock_steps=8, listen_s=3, open_url=lambda *a: Description())
        self.assertEqual(found["192.168.0.20"]["hostname"], "tv")


if __name__ == "__main__":
    unittest.main()
