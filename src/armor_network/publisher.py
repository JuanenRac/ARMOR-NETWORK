"""Delivery of the network state to an explicitly chosen ARMOR-SERVER.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.
"""

from __future__ import annotations

import json
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .orders import Order, parse_orders

ROUTE = "/api/v1/network/state"


class DeliveryError(RuntimeError):
    """The server refused or could not be reached."""


def check_server_url(server_url: str) -> str:
    """Only a plain http(s) origin is accepted: no credentials, path or query in the URL."""
    parsed = urlparse(server_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.path not in ("", "/") or parsed.query:
        raise ValueError("--server-url must be a plain http(s) origin such as http://127.0.0.1:8080")
    return f"{parsed.scheme}://{parsed.netloc}"


def _send(server_url: str, token: str, payload: dict, timeout: float, attempts: int, pause_s: float) -> tuple[int, object]:
    request = Request(f"{server_url.rstrip('/')}{ROUTE}", data=json.dumps(payload).encode(), method="POST",
                      headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    last = "no attempt was made"
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - the scheme is checked by check_server_url
                if response.status != 202:
                    raise DeliveryError(f"server returned {response.status}")
                try:
                    return response.status, json.loads(response.read(16_384).decode("utf-8", "replace"))
                except ValueError:
                    return response.status, None         # an older server answers with no body worth reading
        except HTTPError as error:
            body = error.read(300).decode("utf-8", "replace")
            error.close()
            if error.code < 500:
                raise DeliveryError(f"server rejected the network state: HTTP {error.code} {body}") from error
            last = f"HTTP {error.code}"
        except OSError:      # includes URLError and a server that accepts the connection and never answers (a timeout)
            last = "server is unreachable"
        if attempt + 1 < attempts:
            time.sleep(pause_s)
    raise DeliveryError(f"{last} after {attempts} attempts")


def post(server_url: str, token: str, payload: dict, timeout: float = 8.0, attempts: int = 2, pause_s: float = 0.5) -> int:
    """POST the state with the ingest token; returns the HTTP status. A 4xx answer is final (the message or the token is wrong); a network error or a 5xx is tried again once."""
    return _send(server_url, token, payload, timeout, attempts, pause_s)[0]


def deliver(server_url: str, token: str, payload: dict, timeout: float = 8.0, attempts: int = 2, pause_s: float = 0.5) -> list[Order]:
    """The same, and the manual orders the server handed out in its answer (the well-formed ones, at most four)."""
    return parse_orders(_send(server_url, token, payload, timeout, attempts, pause_s)[1])
