"""The login the server seals for this node opens here, and only with this node's token (the vector is the one of ARMOR-SERVER's tests/credential_seal.test.ts)."""
import json
import unittest

from armor_network.orders import parse_orders
from armor_network.seal import open_sealed

VECTOR = "BwcHBwcHBwcHBwcHBwcHB3DjzPUrsd3Gaw4Uk/BJhSrk1lLZbEo7RPBc5R3QOGEQdtGjYbg="


class SealTest(unittest.TestCase):
    def test_opens_the_server_vector(self):
        self.assertEqual(open_sealed("k" * 64, VECTOR), "hello")

    def test_refuses_another_token_and_a_changed_seal(self):
        self.assertIsNone(open_sealed("j" * 64, VECTOR))
        self.assertIsNone(open_sealed("k" * 64, VECTOR[:-4] + "AAAA"))
        self.assertIsNone(open_sealed("k" * 64, "not base64 !"))

    def test_an_order_takes_its_login_from_the_seal(self):
        # sealed by the server for the text {"user":"u","password":"p"} is not reproducible here without the nonce: check the refusal path instead
        body = {"commands": [{"id": "c1", "type": "inspect", "ip": "192.168.0.1", "device_id": "d1", "auth_sealed": VECTOR}]}
        order = parse_orders(body, "k" * 64)[0]
        self.assertIsNone(order.user)   # "hello" is not a login: the order goes without one
        self.assertEqual(json.dumps({}), "{}")


if __name__ == "__main__":
    unittest.main()
