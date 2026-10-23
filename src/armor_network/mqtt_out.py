"""Publishing the network state to an MQTT broker, as the second way out (the first is the server's own route).

A node that publishes only here never receives the manual orders: those travel in the answer of the server's route and are never sent over MQTT. The client is the smallest one that
does the job (MQTT 3.1.1, QoS 0, one connection per message, a user name and a password, with or without TLS) so that the project stays free of dependencies.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.
"""

from __future__ import annotations

import re
import socket
import ssl
from urllib.parse import urlparse

MAX_PAYLOAD = 256 * 1024
NODE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class MqttError(RuntimeError):
    """The broker could not be reached or refused the message."""


def check_mqtt_url(url: str) -> str:
    """Only `mqtt://host[:port]` or `mqtts://host[:port]`: no login, path or query in the address (the login has its own settings)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("mqtt", "mqtts") or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query:
        raise ValueError("--mqtt-url must be a plain mqtt:// or mqtts:// address such as mqtt://192.168.0.180:18883")
    return f"{parsed.scheme}://{parsed.netloc}"


def _text(value: str) -> bytes:
    raw = value.encode("utf-8")
    return len(raw).to_bytes(2, "big") + raw


def _length(size: int) -> bytes:
    out = bytearray()
    while True:
        digit, size = size % 128, size // 128
        out.append(digit | (0x80 if size else 0))
        if not size:
            return bytes(out)


def connect_packet(client_id: str, user: str, password: str, keepalive: int = 30) -> bytes:
    flags = 0x02 | (0x80 if user else 0) | (0x40 if user and password else 0)       # clean session, user name, password (a password without a user name is not allowed)
    body = _text("MQTT") + bytes([4, flags]) + keepalive.to_bytes(2, "big") + _text(client_id)
    if user:
        body += _text(user) + (_text(password) if password else b"")
    return b"\x10" + _length(len(body)) + body


def publish_packet(topic: str, payload: bytes) -> bytes:
    body = _text(topic) + payload
    return b"\x30" + _length(len(body)) + body


def publish(url: str, topic: str, payload: bytes, user: str = "", password: str = "", client_id: str = "armor-network", timeout: float = 6.0) -> None:
    """Connect, send one message and say goodbye. Raises MqttError when the broker is not there, does not accept the login or the connection is cut."""
    if len(payload) > MAX_PAYLOAD:
        raise MqttError("the message is too large for the broker")
    parsed = urlparse(check_mqtt_url(url))
    secure = parsed.scheme == "mqtts"
    port = parsed.port or (8883 if secure else 1883)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout) as plain:
            connection = ssl.create_default_context().wrap_socket(plain, server_hostname=parsed.hostname) if secure else plain
            connection.settimeout(timeout)
            connection.sendall(connect_packet(client_id, user, password))
            answer = b""
            while len(answer) < 4:
                chunk = connection.recv(4 - len(answer))
                if not chunk:
                    raise MqttError("the broker closed the connection")
                answer += chunk
            if answer[0] != 0x20 or answer[1] != 2:
                raise MqttError("the broker did not answer the connection the way MQTT does")
            if answer[3] != 0:
                raise MqttError(f"the broker refused the login (code {answer[3]})")
            connection.sendall(publish_packet(topic, payload) + b"\xe0\x00")
    except (OSError, ssl.SSLError) as error:
        raise MqttError(f"the broker could not be reached: {error.__class__.__name__}") from error
