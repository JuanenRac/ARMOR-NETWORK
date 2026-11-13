"""The paths of the look at a device's web page that need a certificate or an odd answer: the connection that checks the certificate before the login, the login that is not sent,
the one that is refused, and the file of certificates that cannot be made private. Stand-ins for the network; nothing leaves this machine."""
import io
import sys
import tempfile
import unittest
import urllib.request
from email.message import Message
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import orders  # noqa: E402


class Answer:
    def __init__(self, status=200, body=b"", server=""):
        self.status = status
        self._body = body
        self.headers = {"Server": server} if server else {}

    def read(self, _limit=None):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def refusal(code, challenge="", body=b""):
    headers = Message()
    if challenge:
        headers["WWW-Authenticate"] = challenge
    return HTTPError("http://192.168.1.9/", code, "x", headers, io.BytesIO(body))


class PinnedConnection(unittest.TestCase):
    def connection(self, der):
        connection = orders._PinnedConnection("192.168.1.9", 443)
        connection.pin_ip, connection.pin_port = "192.168.1.9", 443
        connection.sock = mock.Mock()
        connection.sock.getpeercert.return_value = der
        return connection

    def test_the_same_or_a_new_certificate_lets_the_connection_go_on(self):
        for state in ("same", "new"):
            with mock.patch.object(orders.HTTPSConnection, "connect"), mock.patch.object(orders, "check_pin", return_value=state):
                self.connection(b"der").connect()

    def test_another_certificate_closes_the_connection_before_the_login_is_sent(self):
        connection = self.connection(b"der")
        with mock.patch.object(orders.HTTPSConnection, "connect"), mock.patch.object(orders, "check_pin", return_value="changed"):
            with self.assertRaises(orders.PinChanged) as raised:
                connection.connect()
        self.assertIsNotNone(raised.exception.shown)
        self.assertIn("not the one seen the first time", str(raised.exception))

    def test_a_certificate_that_cannot_be_read_is_treated_as_another_one(self):
        for der in (None, b""):
            connection = self.connection(der)
            with mock.patch.object(orders.HTTPSConnection, "connect"):
                with self.assertRaises(orders.PinChanged) as raised:
                    connection.connect()
            self.assertIsNone(raised.exception.shown)
            self.assertIn("could not be read", str(raised.exception))

    def test_a_connection_with_no_socket_is_also_refused(self):
        connection = orders._PinnedConnection("192.168.1.9", 443)
        connection.sock = None
        with mock.patch.object(orders.HTTPSConnection, "connect"):
            with self.assertRaises(orders.PinChanged):
                connection.connect()

    def test_the_handler_opens_with_the_connection_of_its_address(self):
        handler = orders._PinnedHandler(None, "192.168.1.9", 443)
        self.assertEqual((handler._connection.pin_ip, handler._connection.pin_port), ("192.168.1.9", 443))
        with mock.patch.object(orders.HTTPSHandler, "do_open", return_value="opened") as do_open:
            self.assertEqual(handler.https_open("request"), "opened")
        self.assertIs(do_open.call_args.args[0], handler._connection)


class Opening(unittest.TestCase):
    def handlers(self, url, user, context=None, pin=None, env=None):
        taken = []

        def build(*handlers):
            taken.extend(handlers)
            return mock.Mock()

        with mock.patch.dict("os.environ", env or {}, clear=False), mock.patch.object(urllib.request, "build_opener", build):
            orders._open(url, user, "secret", context, 1.0, pin=pin)
        return [type(handler).__name__ for handler in taken]

    def test_basic_is_offered_only_over_https_or_when_the_owner_allowed_it(self):
        self.assertNotIn("HTTPBasicAuthHandler", self.handlers("http://192.168.1.9/", "admin", env={"ARMOR_NETWORK_ALLOW_BASIC_HTTP": "0"}))
        self.assertIn("HTTPBasicAuthHandler", self.handlers("http://192.168.1.9/", "admin", env={"ARMOR_NETWORK_ALLOW_BASIC_HTTP": "1"}))
        self.assertIn("HTTPBasicAuthHandler", self.handlers("https://192.168.1.9/", "admin"))
        self.assertNotIn("HTTPDigestAuthHandler", self.handlers("http://192.168.1.9/", None))

    def test_a_context_with_a_pin_uses_the_pinned_handler_and_without_it_the_plain_one(self):
        import ssl
        context = ssl.create_default_context()
        self.assertIn("_PinnedHandler", self.handlers("https://192.168.1.9/", "admin", context, pin=("192.168.1.9", 443)))
        names = self.handlers("https://192.168.1.9/", "admin", context)
        self.assertIn("HTTPSHandler", names)
        self.assertNotIn("_PinnedHandler", names)


class Inspecting(unittest.TestCase):
    def inspect(self, first, second=None, user="admin", password="hunter22", port=80, env=None):
        calls = [first] if second is None else [first, second]

        def fake(url, who, pwd, context, timeout, pin=None):
            item = calls.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item

        with mock.patch.object(orders, "_open", fake), mock.patch.dict("os.environ", env or {}, clear=False):
            return orders._inspect_one("192.168.1.9", port, user, password, 1.0)

    def test_a_page_that_does_not_answer_is_none(self):
        self.assertIsNone(self.inspect(OSError("down")))

    def test_without_a_login_it_says_that_one_is_required_and_which_kind(self):
        result = self.inspect(refusal(401, 'Digest realm="camera"'), user=None, password=None)
        self.assertIn("required (Digest), no login was given; realm: camera", result["output"])

    def test_a_basic_login_over_plain_http_is_not_sent(self):
        result = self.inspect(refusal(401, 'Basic realm="x"'), env={"ARMOR_NETWORK_ALLOW_BASIC_HTTP": "0"})
        self.assertFalse(result["ok"])
        self.assertIn("not sent: the device asks for Basic over plain HTTP", result["output"])

    def test_a_login_the_device_refuses_is_told_with_its_status(self):
        result = self.inspect(refusal(401, 'Digest realm="x"'), refusal(401, 'Digest realm="x"'))
        self.assertFalse(result["ok"])
        self.assertIn("login: refused;", result["output"])
        result = self.inspect(refusal(401, 'Digest realm="x"'), refusal(403))
        self.assertIn("refused (HTTP 403)", result["output"])

    def test_a_certificate_that_changed_stops_the_login(self):
        result = self.inspect(refusal(401, 'Basic realm="x"'), orders.PinChanged("ab" * 32), port=443)
        self.assertFalse(result["ok"])
        self.assertIn("not sent: the HTTPS certificate of this device is not the one seen the first time", result["output"])

    def test_a_connection_that_breaks_during_the_login_is_not_tried(self):
        result = self.inspect(refusal(401, 'Digest realm="x"'), OSError("reset by peer"))
        self.assertFalse(result["ok"])
        self.assertIn("login: not tried: reset by peer", result["output"])

    def test_an_accepted_factory_login_says_to_change_it_and_the_password_is_never_echoed(self):
        page = Answer(200, b"<title>Router</title> admin hunter22", server="Boa")
        result = self.inspect(refusal(401, 'Digest realm="x"'), page, user="admin", password="admin")
        self.assertTrue(result["ok"])
        self.assertIn("accepted (Digest) - it is a factory login: change it", result["output"])
        page = Answer(200, b"<title>Router hunter22</title>")
        result = self.inspect(refusal(401, 'Digest realm="x"'), page, user="root", password="hunter22")
        self.assertNotIn("hunter22", result["output"])
        self.assertIn("***", result["output"])


class PinFile(unittest.TestCase):
    def test_a_file_that_cannot_be_made_private_is_still_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pins.json"
            with mock.patch.object(orders.os, "chmod", side_effect=OSError("no")):
                self.assertEqual(orders.check_pin("192.168.1.9", 443, "aa", path), "new")
            self.assertEqual(orders.check_pin("192.168.1.9", 443, "aa", path), "same")


if __name__ == "__main__":
    unittest.main()
