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
        import base64
        import hashlib
        import hmac
        from armor_network import seal as sealing

        def seal_for(token, text, nonce=b"" * 16):   # the same construction as ARMOR-SERVER's credential_seal.ts, with a fixed nonce
            data = text.encode()
            cipher = bytes(a ^ b for a, b in zip(data, sealing._stream(sealing._sub_key(token, "enc"), nonce, len(data))))
            tag = hmac.new(sealing._sub_key(token, "mac"), nonce + cipher, hashlib.sha256).digest()
            return base64.b64encode(nonce + cipher + tag).decode()

        self.assertEqual(seal_for("k" * 64, "hello"), VECTOR)    # the construction here is the server's, byte for byte
        sealed = seal_for("k" * 64, json.dumps({"user": "u", "password": "p"}))
        body = {"commands": [{"id": "c1", "type": "inspect", "ip": "192.168.0.1", "device_id": "d1", "auth_sealed": sealed}]}
        order = parse_orders(body, "k" * 64)[0]
        self.assertEqual((order.user, order.password), ("u", "p"))
        self.assertIsNone(parse_orders(body, "j" * 64)[0].user)              # another token opens nothing
        withheld = parse_orders(body, "k" * 64, allow_login=False)[0]        # plain http across the network: never opened
        self.assertIsNone(withheld.user)
        self.assertTrue(withheld.login_withheld)
        plain = {"commands": [{"id": "c2", "type": "inspect", "ip": "192.168.0.1", "auth_sealed": VECTOR}]}
        self.assertIsNone(parse_orders(plain, "k" * 64)[0].user)             # "hello" is not a login

if __name__ == "__main__":
    unittest.main()
