"""Edge cases of the readers that take bytes and text from the network: the DNS message reader, the sealed login, the MQTT sender, the delivery to the server, the vendor table and the guess of a device's kind."""
import base64
import hashlib
import hmac
import io
import os
import socket
import ssl
import struct
import sys
import unittest
from unittest import mock
from urllib.error import HTTPError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from armor_network import dnswire, mqtt_out, oui, publisher, seal, services  # noqa: E402


def header(qd=0, an=0, ns=0, ar=0, flags=0x8180):
    return struct.pack(">HHHHHH", 1, flags, qd, an, ns, ar)


def record(name_bytes, rtype, rdata, ttl=60):
    return name_bytes + struct.pack(">HHIH", rtype, 1, ttl, len(rdata)) + rdata


class DnsReaderEdges(unittest.TestCase):
    def test_a_name_with_an_empty_or_long_label_is_refused(self):
        with self.assertRaises(ValueError):
            dnswire.encode_name("a..b")
        with self.assertRaises(ValueError):
            dnswire.encode_name("x" * 64 + ".local")

    def test_a_name_that_runs_past_the_message(self):
        with self.assertRaises(ValueError):
            dnswire.read_name(b"\x03ab", 0)       # the label says 3 bytes and 2 are left
        with self.assertRaises(ValueError):
            dnswire.read_name(b"\x03abc", 0)      # no terminating zero
        with self.assertRaises(ValueError):
            dnswire.read_name(b"\xc0", 0)         # a pointer with no second byte

    def test_a_pointer_forwards_or_in_a_loop_is_refused(self):
        with self.assertRaises(ValueError):
            dnswire.read_name(b"\xc0\x05\x00\x00\x00\x00", 0)
        loop = b"\x01a\xc0\x00"
        with self.assertRaises(ValueError):
            dnswire.read_name(loop, 2)

    def test_an_unknown_label_type_and_a_name_over_255_bytes_are_refused(self):
        with self.assertRaises(ValueError):
            dnswire.read_name(b"\x40abc\x00", 0)
        long_name = b"".join(b"\x3f" + b"a" * 63 for _ in range(5)) + b"\x00"
        with self.assertRaises(ValueError):
            dnswire.read_name(long_name, 0)

    def test_a_pointer_to_an_earlier_name_is_followed(self):
        data = b"\x03abc\x00" + b"\x01z\xc0\x00"
        name, end = dnswire.read_name(data, 5)
        self.assertEqual(name, "z.abc")
        self.assertEqual(end, len(data))

    def test_a_message_shorter_than_its_header_or_too_big_is_refused(self):
        with self.assertRaises(ValueError):
            dnswire.parse_message(b"\x00" * 11)
        with self.assertRaises(ValueError):
            dnswire.parse_message(header(qd=33))
        with self.assertRaises(ValueError):
            dnswire.parse_message(header(an=200, ns=40, ar=40))

    def test_a_question_or_a_record_cut_short_is_refused(self):
        with self.assertRaises(ValueError):
            dnswire.parse_message(header(qd=1) + dnswire.encode_name("a.local") + b"\x00")
        with self.assertRaises(ValueError):
            dnswire.parse_message(header(an=1) + dnswire.encode_name("a.local") + b"\x00\x01")
        cut = header(an=1) + dnswire.encode_name("a.local") + struct.pack(">HHIH", 1, 1, 60, 4) + b"\x01"
        with self.assertRaises(ValueError):
            dnswire.parse_message(cut)

    def test_records_of_each_kind_are_decoded(self):
        name = dnswire.encode_name("printer.local")
        target = dnswire.encode_name("host.local")
        srv = struct.pack(">HHH", 0, 0, 631) + target
        txt = b"\x05ty=ab" + b"\x03x=1"
        data = (header(qd=1, an=5) + name + struct.pack(">HH", 12, 1)
                + record(name, 1, bytes([192, 168, 0, 7]))
                + record(name, 12, target)
                + record(name, 33, srv)
                + record(name, 16, txt)
                + record(name, 99, b"\x01\x02"))
        message = dnswire.parse_message(data)
        self.assertEqual(message["questions"], [("printer.local", 12)])
        answers = message["answers"]
        self.assertEqual(answers[0]["data"], "192.168.0.7")
        self.assertEqual(answers[1]["data"], "host.local")
        self.assertEqual(answers[2]["data"], {"port": 631, "target": "host.local"})
        self.assertEqual(answers[3]["data"], ["ty=ab", "x=1"])
        self.assertEqual(answers[4]["data"], b"\x01\x02")
        self.assertEqual(dnswire.rcode(message), 0)

    def test_the_response_code_is_the_low_four_bits(self):
        self.assertEqual(dnswire.rcode({"flags": 0x8183}), 3)


class SealEdges(unittest.TestCase):
    def test_a_message_too_short_to_hold_a_tag_gives_nothing(self):
        self.assertIsNone(seal.open_sealed("k" * 64, base64.b64encode(b"x" * 47).decode()))

    def test_a_valid_tag_over_bytes_that_are_not_text_gives_nothing(self):
        token = "k" * 64
        nonce = bytes(range(16))
        plain = b"\xff\xfe\xfd"
        stream = seal._stream(seal._sub_key(token, "enc"), nonce, len(plain))
        cipher = bytes(a ^ b for a, b in zip(plain, stream, strict=False))
        tag = hmac.new(seal._sub_key(token, "mac"), nonce + cipher, hashlib.sha256).digest()
        blob = base64.b64encode(nonce + cipher + tag).decode()
        self.assertIsNone(seal.open_sealed(token, blob))

    def test_a_long_secret_uses_more_than_one_block_of_stream(self):
        token = "k" * 64
        nonce = b"\x07" * 16
        plain = ("long secret " * 12).encode()
        stream = seal._stream(seal._sub_key(token, "enc"), nonce, len(plain))
        cipher = bytes(a ^ b for a, b in zip(plain, stream, strict=False))
        tag = hmac.new(seal._sub_key(token, "mac"), nonce + cipher, hashlib.sha256).digest()
        self.assertEqual(seal.open_sealed(token, base64.b64encode(nonce + cipher + tag).decode()), plain.decode())


class FakeSocket:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def settimeout(self, value):
        pass

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        return self.replies.pop(0) if self.replies else b""


class MqttSenderEdges(unittest.TestCase):
    def send(self, replies, url="mqtt://broker.local"):
        fake = FakeSocket(replies)
        with mock.patch.object(mqtt_out.socket, "create_connection", return_value=fake):
            mqtt_out.publish(url, "armor/x", b"{}")
        return fake

    def test_a_cut_connection_before_the_answer_is_an_error(self):
        with self.assertRaises(mqtt_out.MqttError):
            self.send([b""])

    def test_an_answer_that_is_not_a_connack_is_an_error(self):
        with self.assertRaises(mqtt_out.MqttError):
            self.send([b"\x30\x02\x00\x00"])

    def test_a_refused_login_names_its_code(self):
        with self.assertRaisesRegex(mqtt_out.MqttError, "code 5"):
            self.send([b"\x20\x02\x00\x05"])

    def test_the_answer_may_come_in_pieces_and_the_message_is_sent_with_the_goodbye(self):
        fake = self.send([b"\x20\x02", b"\x00\x00"])
        self.assertEqual(len(fake.sent), 2)
        self.assertTrue(fake.sent[1].endswith(b"\xe0\x00"))

    def test_a_secure_url_wraps_the_socket_with_a_tls_context_of_1_2_or_more(self):
        plain = FakeSocket([])
        wrapped = FakeSocket([b"\x20\x02\x00\x00"])
        context = mock.Mock()
        context.wrap_socket.return_value = wrapped
        with mock.patch.object(mqtt_out.socket, "create_connection", return_value=plain), \
                mock.patch.object(mqtt_out.ssl, "create_default_context", return_value=context):
            mqtt_out.publish("mqtts://broker.local", "armor/x", b"{}")
        self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
        context.wrap_socket.assert_called_once()
        self.assertEqual(len(wrapped.sent), 2)

    def test_a_tls_failure_becomes_a_broker_error(self):
        with mock.patch.object(mqtt_out.socket, "create_connection", side_effect=ssl.SSLError("bad certificate")):
            with self.assertRaisesRegex(mqtt_out.MqttError, "could not be reached"):
                mqtt_out.publish("mqtts://broker.local", "armor/x", b"{}")

    def test_a_message_over_the_limit_is_refused_before_connecting(self):
        with mock.patch.object(mqtt_out.socket, "create_connection") as connect:
            with self.assertRaises(mqtt_out.MqttError):
                mqtt_out.publish("mqtt://broker.local", "armor/x", b"x" * (mqtt_out.MAX_PAYLOAD + 1))
        connect.assert_not_called()


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size):
        return self._body[:size]


class DeliveryEdges(unittest.TestCase):
    def test_an_answer_other_than_202_is_an_error_that_is_tried_again_no_more_than_the_attempts(self):
        calls = []

        def answer(request, timeout):
            calls.append(1)
            return FakeResponse(200, b"{}")
        with mock.patch.object(publisher, "urlopen", side_effect=answer):
            with self.assertRaises(publisher.DeliveryError):
                publisher.post("https://server.local", "t" * 64, {}, attempts=1, pause_s=0)
        self.assertEqual(len(calls), 1)

    def test_a_body_that_is_not_json_is_accepted_with_no_orders(self):
        with mock.patch.object(publisher, "urlopen", return_value=FakeResponse(202, b"accepted")):
            self.assertEqual(publisher.post("https://server.local", "t" * 64, {}), 202)

    def test_a_4xx_is_final_and_a_5xx_is_tried_again(self):
        def http_error(code):
            return HTTPError("https://server.local", code, "x", {}, io.BytesIO(b"no"))
        with mock.patch.object(publisher, "urlopen", side_effect=http_error(403)) as sender:
            with self.assertRaisesRegex(publisher.DeliveryError, "403"):
                publisher.post("https://server.local", "t" * 64, {}, attempts=3, pause_s=0)
        self.assertEqual(sender.call_count, 1)
        with mock.patch.object(publisher, "urlopen", side_effect=[http_error(503), http_error(503)]) as sender, \
                mock.patch.object(publisher.time, "sleep") as sleeper:
            with self.assertRaisesRegex(publisher.DeliveryError, "after 2 attempts"):
                publisher.post("https://server.local", "t" * 64, {}, attempts=2, pause_s=0.25)
        self.assertEqual(sender.call_count, 2)
        sleeper.assert_called_once_with(0.25)

    def test_a_server_that_does_not_answer_is_unreachable(self):
        with mock.patch.object(publisher, "urlopen", side_effect=socket.timeout("slow")):
            with self.assertRaisesRegex(publisher.DeliveryError, "unreachable"):
                publisher.post("https://server.local", "t" * 64, {}, attempts=1, pause_s=0)

    def test_a_login_travels_only_over_https_or_to_this_machine(self):
        self.assertTrue(publisher.login_may_travel("https://armor.example"))
        self.assertTrue(publisher.login_may_travel("http://localhost:3000"))
        self.assertTrue(publisher.login_may_travel("http://127.0.0.1:3000"))
        self.assertTrue(publisher.login_may_travel("http://[::1]:3000"))
        self.assertFalse(publisher.login_may_travel("http://192.168.0.5:3000"))
        self.assertFalse(publisher.login_may_travel("http://server.local"))
        self.assertFalse(publisher.login_may_travel("ftp://"))


class VendorTableEdges(unittest.TestCase):
    def test_a_missing_table_file_gives_an_empty_table(self):
        oui._table.cache_clear()
        try:
            with mock.patch.object(oui.resources, "files", side_effect=FileNotFoundError("no table")):
                self.assertEqual(oui._table(), {})
        finally:
            oui._table.cache_clear()

    def test_lines_without_a_six_digit_prefix_or_a_name_are_skipped(self):
        import gzip
        raw = gzip.compress(b"AABBCC\tMaker One\nAABB\tShort\nDDEEFF\t\nnoprefix\n")

        class Resource:
            def joinpath(self, *names):
                return self

            def read_bytes(self):
                return raw
        oui._table.cache_clear()
        try:
            with mock.patch.object(oui.resources, "files", return_value=Resource()):
                self.assertEqual(oui._table(), {"AABBCC": "Maker One"})
        finally:
            oui._table.cache_clear()


class KindGuessEdges(unittest.TestCase):
    def test_the_gateway_comes_first_then_what_the_device_does(self):
        self.assertEqual(services.guess_kind(is_gateway=True, ports={554}), "router")
        self.assertEqual(services.guess_kind(ports={8554}), "camera")
        self.assertEqual(services.guess_kind(ports={9100}), "printer")
        self.assertEqual(services.guess_kind(ports={8009}), "tv")
        self.assertEqual(services.guess_kind(ports={32400}), "nas")

    def test_a_phone_made_by_a_maker_of_computers_is_not_a_computer(self):
        kind = services.guess_kind(vendor="Apple, Inc.", hostname="Juan-iPhone")
        self.assertEqual(kind, "phone")
        self.assertEqual(services.guess_kind(vendor="Apple, Inc.", ports={22}), "computer")
        self.assertEqual(services.guess_kind(vendor="Apple, Inc."), "phone")

    def test_a_device_with_industrial_ports_is_iot_unless_it_also_has_a_shell(self):
        self.assertEqual(services.guess_kind(ports={1883}), "iot")
        self.assertEqual(services.guess_kind(ports={1883, 22}), "server")

    def test_windows_ports_mean_a_computer(self):
        self.assertEqual(services.guess_kind(ports={445}), "computer")


if __name__ == "__main__":
    unittest.main()
