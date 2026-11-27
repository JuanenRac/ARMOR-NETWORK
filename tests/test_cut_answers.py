# ARMOR-NETWORK - tests/test_cut_answers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.
"""Answers cut in the middle or that are not HTTP, from the server, a public service, the router or a device. Nothing leaves the machine."""
from __future__ import annotations

import http.client
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import orders, publisher, system_io  # noqa: E402

BROKEN = (http.client.IncompleteRead(b"{", 100), http.client.BadStatusLine("SSH-2.0-OpenSSH"))


class CutAnswerTests(unittest.TestCase):
    def test_a_cut_answer_of_the_server_is_a_delivery_error(self) -> None:
        for broken in BROKEN:
            with mock.patch.object(publisher, "urlopen", side_effect=broken) as opened:
                with self.assertRaises(publisher.DeliveryError):
                    publisher.post("http://127.0.0.1:1", "t", {"node_id": "n"}, attempts=2, pause_s=0)
                self.assertEqual(opened.call_count, 2)   # asked again, like an unreachable server

    def test_a_cut_public_address_answer_is_nothing_known(self) -> None:
        for broken in BROKEN:
            with mock.patch.object(orders, "urlopen", side_effect=broken):
                self.assertIsNone(orders.fetch_public_info())

    def test_a_router_that_answers_garbage_is_no_answer(self) -> None:
        opener = mock.Mock()
        for broken in BROKEN:
            opener.open.side_effect = broken
            with mock.patch.object(system_io, "build_opener", return_value=opener):
                self.assertEqual(system_io._router_http("http://192.168.1.1/x", b"", {}, None, None), (0, ""))


if __name__ == "__main__":
    unittest.main()
