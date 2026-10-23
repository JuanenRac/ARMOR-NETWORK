"""The MQTT way out: the packets are the ones MQTT 3.1.1 defines, a broker that refuses the login is an error and not a crash, and the command line sends the message there."""
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from armor_network import mqtt_out  # noqa: E402
from armor_network.cli import main  # noqa: E402


def read_packet(connection):
    first = connection.recv(1)
    multiplier, size = 1, 0
    while True:
        digit = connection.recv(1)[0]
        size += (digit & 127) * multiplier
        multiplier *= 128
        if not digit & 128:
            break
    body = b""
    while len(body) < size:
        body += connection.recv(size - len(body))
    return first[0], body


class Broker:
    """A broker that accepts one connection, answers the CONNECT with the code it was told to and keeps what it was sent."""

    def __init__(self, code=0):
        self.code, self.packets = code, []
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(4)
        self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while True:
            try:
                connection, _ = self.server.accept()
            except OSError:
                return
            with connection:
                try:
                    self.packets.append(read_packet(connection))
                    connection.sendall(bytes([0x20, 2, 0, self.code]))
                    if self.code == 0:
                        self.packets.append(read_packet(connection))
                        self.packets.append(read_packet(connection))
                except (OSError, IndexError):
                    pass

    def close(self):
        self.server.close()


class PacketTests(unittest.TestCase):
    def test_the_length_is_the_variable_one_of_mqtt(self):
        self.assertEqual(mqtt_out._length(0), b"\x00")
        self.assertEqual(mqtt_out._length(127), b"\x7f")
        self.assertEqual(mqtt_out._length(128), b"\x80\x01")
        self.assertEqual(mqtt_out._length(16383), b"\xff\x7f")
        self.assertEqual(mqtt_out._length(16384), b"\x80\x80\x01")

    def test_the_connect_packet_carries_the_login_only_when_there_is_one(self):
        anonymous = mqtt_out.connect_packet("armor-network-n1", "", "")
        self.assertEqual(anonymous[0], 0x10)
        self.assertEqual(anonymous[2:9], b"\x00\x04MQTT\x04")
        self.assertEqual(anonymous[9], 0x02)
        with_login = mqtt_out.connect_packet("armor-network-n1", "network-node-n1", "secret")
        self.assertEqual(with_login[9], 0x02 | 0x80 | 0x40)
        self.assertIn(b"network-node-n1", with_login)
        self.assertTrue(with_login.endswith(b"\x00\x06secret"))
        self.assertEqual(mqtt_out.connect_packet("x", "u", "")[9], 0x02 | 0x80)
        self.assertEqual(mqtt_out.connect_packet("x", "", "orphan")[9], 0x02, "a password without a user name is not sent")

    def test_only_a_plain_broker_address_is_taken(self):
        self.assertEqual(mqtt_out.check_mqtt_url("mqtt://192.168.0.180:18883"), "mqtt://192.168.0.180:18883")
        self.assertEqual(mqtt_out.check_mqtt_url("mqtts://broker.example"), "mqtts://broker.example")
        for bad in ("http://x", "mqtt://u:p@x", "mqtt://x/topic", "mqtt://x?a=1", "x", ""):
            with self.subTest(bad), self.assertRaises(ValueError):
                mqtt_out.check_mqtt_url(bad)


class BrokerTests(unittest.TestCase):
    def test_a_message_reaches_the_broker_as_a_qos_zero_publish_with_the_login(self):
        broker = Broker()
        try:
            mqtt_out.publish(f"mqtt://127.0.0.1:{broker.port}", "armor/network/n1/state", b'{"kind":"network"}', "network-node-n1", "pw", "armor-network-n1")
            broker.thread.join(2)
        finally:
            broker.close()
        kinds = [first for first, _ in broker.packets]
        self.assertEqual(kinds, [0x10, 0x30, 0xE0])
        topic_length = int.from_bytes(broker.packets[1][1][:2], "big")
        self.assertEqual(broker.packets[1][1][2:2 + topic_length], b"armor/network/n1/state")
        self.assertEqual(broker.packets[1][1][2 + topic_length:], b'{"kind":"network"}')

    def test_a_refused_login_a_missing_broker_and_a_huge_message_are_errors_not_crashes(self):
        broker = Broker(code=5)
        try:
            with self.assertRaises(mqtt_out.MqttError) as caught:
                mqtt_out.publish(f"mqtt://127.0.0.1:{broker.port}", "armor/network/n1/state", b"{}", "u", "bad")
            self.assertIn("refused the login", str(caught.exception))
        finally:
            broker.close()
        free = socket.socket()
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
        free.close()
        with self.assertRaises(mqtt_out.MqttError):
            mqtt_out.publish(f"mqtt://127.0.0.1:{port}", "armor/network/n1/state", b"{}", timeout=1)
        with self.assertRaises(mqtt_out.MqttError):
            mqtt_out.publish("mqtt://127.0.0.1:1", "t", b"x" * (mqtt_out.MAX_PAYLOAD + 1))


class CommandLineTests(unittest.TestCase):
    def test_the_demo_publishes_to_the_broker_when_asked_and_validates_against_the_contract(self):
        broker = Broker()
        try:
            with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"ARMOR_NETWORK_MQTT_PASSWORD": "pw"}):
                code = main(["demo", "--count", "1", "--tick-s", "2", "--data-dir", folder, "--no-public-info", "--mqtt-url", f"mqtt://127.0.0.1:{broker.port}", "--mqtt-user", "network-node-network-1"])
            broker.thread.join(2)
        finally:
            broker.close()
        self.assertEqual(code, 0)
        message = json.loads(broker.packets[1][1][2 + int.from_bytes(broker.packets[1][1][:2], "big"):])
        self.assertEqual(message["kind"], "network")

    def test_a_bad_broker_address_or_a_password_without_a_user_is_a_message_not_a_traceback(self):
        for arguments in (["--mqtt-url", "http://x"], ["--mqtt-url", "mqtt://127.0.0.1:1"]):
            with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"ARMOR_NETWORK_MQTT_PASSWORD": "pw"}):
                code = main(["demo", "--count", "1", "--tick-s", "2", "--data-dir", folder, "--no-public-info", *arguments])
            self.assertEqual(code, 2, arguments)


if __name__ == "__main__":
    unittest.main()
