"""The real system layer (threads, sockets, subprocess) that the other tests replace with a stand-in: what can be tried without a network."""
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from armor_network import system_io  # noqa: E402


class BoundedTests(unittest.TestCase):
    def test_a_quick_call_gives_its_answer(self):
        self.assertEqual(system_io.bounded(lambda: 42, 1.0), 42)

    def test_a_call_that_fails_with_an_os_error_gives_none(self):
        def broken():
            raise OSError("no route")
        self.assertIsNone(system_io.bounded(broken, 1.0))
        def bad_text():
            raise UnicodeError("not text")
        self.assertIsNone(system_io.bounded(bad_text, 1.0))

    def test_a_slow_call_is_given_up_on_and_counted_until_it_ends(self):
        release = threading.Event()
        started = time.monotonic()
        self.assertIsNone(system_io.bounded(lambda: release.wait(5) and "late", 0.05))
        self.assertLess(time.monotonic() - started, 1.0)       # it did not wait for the slow call
        self.assertGreaterEqual(system_io.stuck_calls(), 1)
        release.set()
        for _ in range(100):
            if system_io.stuck_calls() == 0:
                break
            time.sleep(0.02)
        self.assertEqual(system_io.stuck_calls(), 0)             # once it ends it is not counted

    def test_stuck_calls_do_not_pile_up(self):
        release = threading.Event()
        try:
            started = 0
            for _ in range(system_io._MAX_STUCK + 10):
                before = system_io.stuck_calls()
                system_io.bounded(lambda: release.wait(5), 0.01)
                if system_io.stuck_calls() > before:
                    started += 1
            self.assertEqual(system_io.stuck_calls(), system_io._MAX_STUCK)
            self.assertLessEqual(started, system_io._MAX_STUCK)
            # with the cap reached, a quick call is not even made
            self.assertIsNone(system_io.bounded(lambda: "never", 1.0))
        finally:
            release.set()
            for _ in range(200):
                if system_io.stuck_calls() == 0:
                    break
                time.sleep(0.02)
        self.assertEqual(system_io.stuck_calls(), 0)
        self.assertEqual(system_io.bounded(lambda: "again", 1.0), "again")   # and it works again when they have ended


class RunTests(unittest.TestCase):
    def test_a_tool_that_is_not_there_gives_an_empty_text(self):
        self.assertEqual(system_io.run(["this-tool-does-not-exist-armor"]), "")

    def test_a_tool_that_takes_too_long_gives_an_empty_text(self):
        self.assertEqual(system_io.run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.3), "")

    def test_a_tool_that_prints_gives_its_text(self):
        self.assertEqual(system_io.run([sys.executable, "-c", "print('hello')"]).strip(), "hello")


if __name__ == "__main__":
    unittest.main()
