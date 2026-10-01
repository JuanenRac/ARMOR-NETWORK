"""Is the internet there, and for how long was it not: the state machine behind the internet check.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Every round the agent asks the router whether it answers and asks a few places on the internet (a TCP connection, a DNS question, a web page that only answers 204). This
module turns those rounds into a state and into events:

  up         at least one of the places answers
  degraded   they answer, but a good part of the rounds fail or the answers are slow
  down       none answers and THE ROUTER DOES: the fault is beyond it (the provider, the line, the router's own connection)
  lan_down   none answers and the router does not either: the fault is on this side (the router is off, the cable, the switch, this machine's network)
  unknown    just started

One failed round is nothing (a lost packet); it takes `down_after` in a row to call it an outage, and `up_after` good ones to call it over, so a line that flaps does not
raise a hundred alarms. An outage is dated from its FIRST failed round, not from the moment it was confirmed, and its length is counted to the first good round. The outages are
kept (in a file, so a restart does not forget them) for the totals of the last 24 hours. While this program is not running nothing is known, and that time is not counted as an
outage.
"""

from __future__ import annotations

import json
import os
import statistics
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from .inventory import EventLog

DAY_MS = 86_400_000


@dataclass
class ProbeResult:
    target: str
    kind: str                 # icmp, tcp, dns or http
    ok: bool
    latency_ms: float | None = None


class InternetMonitor:
    def __init__(self, path: Path | None = None, *, log: EventLog | None = None, down_after: int = 3, up_after: int = 2, degraded_loss: float = 20.0,
                 recovered_loss: float = 10.0, degraded_latency_ms: float = 300.0, recovered_latency_ms: float = 200.0, window_s: int = 60) -> None:
        self.path = path
        self.log = log or EventLog()
        self.down_after, self.up_after = down_after, up_after
        self.degraded_loss, self.recovered_loss = degraded_loss, recovered_loss
        self.degraded_latency, self.recovered_latency = degraded_latency_ms, recovered_latency_ms
        self.window_ms = window_s * 1000
        self.state = "unknown"
        self.since_ms: int | None = None
        self.gateway_ok: bool | None = None
        self.latency_ms: float | None = None
        self.probes: list[ProbeResult] = []
        self.history: list[dict] = []          # finished outages: {"started_ms", "ended_ms"}
        self._fail_streak = 0
        self._ok_streak = 0
        self._gateway_fail_streak = 0         # rounds in a row in which the router did not answer: one lost echo is not a router that is down
        self._first_fail_ms: int | None = None
        self._first_ok_ms: int | None = None
        self._outage_start_ms: int | None = None
        self._gateway_down_ms: int | None = None
        self._rounds: deque[tuple[int, bool]] = deque()   # (time, the round was good)
        self._last_feed_ms: int | None = None
        if path is not None:
            self.load()

    # ---- one round ---------------------------------------------------------------------------------------------------------------------------
    def feed(self, now_ms: int, gateway_ok: bool | None, results: list[ProbeResult]) -> list[dict]:
        """One round: whether the router answered and what the probes of the internet did. Returns the events it caused."""
        events: list[dict] = []
        self.gateway_ok, self.probes, self._last_feed_ms = gateway_ok, list(results), now_ms
        self._gateway_fail_streak = self._gateway_fail_streak + 1 if gateway_ok is False else 0
        any_ok = any(r.ok for r in results)
        good_round = bool(results) and sum(1 for r in results if r.ok) * 2 >= len(results)
        self._rounds.append((now_ms, good_round))
        while self._rounds and now_ms - self._rounds[0][0] > self.window_ms:
            self._rounds.popleft()
        # The latency of the line is what a ping, a connection and a DNS answer take: a whole web page (a TLS handshake, a redirect, the other end's own load)
        # is often a few hundred ms on a perfectly good line, and counting it made a healthy connection look slow.
        latencies = [r.latency_ms for r in results if r.ok and r.latency_ms is not None and r.kind != "http"]
        if not latencies:
            latencies = [r.latency_ms for r in results if r.ok and r.latency_ms is not None]
        self.latency_ms = round(statistics.median(latencies), 1) if latencies else None
        if any_ok:
            self._ok_streak += 1
            self._fail_streak = 0
            self._first_fail_ms = None
            if self._first_ok_ms is None:
                self._first_ok_ms = now_ms
        else:
            self._fail_streak += 1
            self._ok_streak = 0
            self._first_ok_ms = None
            if self._first_fail_ms is None:
                self._first_fail_ms = now_ms

        if self.state in ("unknown", "up", "degraded"):
            if not any_ok and self._fail_streak >= self.down_after:
                start = self._first_fail_ms if self._first_fail_ms is not None else now_ms
                self._outage_start_ms = start
                lan = self._gateway_fail_streak >= 2
                events.append(self.log.add("internet_down", start, detail="the router does not answer either" if lan else "the router answers and nothing beyond it does"))
                if lan:
                    self._gateway_down_ms = start
                    events.append(self.log.add("gateway_down", start, detail="the router does not answer"))
                self._enter("lan_down" if lan else "down", start)
            elif any_ok:
                target = self._quality()
                if target != self.state:
                    self._enter(target, now_ms)
        else:   # down or lan_down: an outage is going on
            if any_ok and self._ok_streak >= self.up_after:
                ended = self._first_ok_ms if self._first_ok_ms is not None else now_ms
                started = self._outage_start_ms if self._outage_start_ms is not None else ended
                seconds = max(0, round((ended - started) / 1000))
                self.history.append({"started_ms": started, "ended_ms": ended})
                self._trim(now_ms)
                events.append(self.log.add("internet_up", ended, outage_s=seconds, detail=f"the internet is back after {seconds} s"))
                if self._gateway_down_ms is not None:
                    events.append(self.log.add("gateway_up", ended, outage_s=max(0, round((ended - self._gateway_down_ms) / 1000)), detail="the router answers again"))
                self._outage_start_ms = self._gateway_down_ms = None
                self._rounds.clear()               # the rounds of the outage are the outage, not loss: the line starts again from good
                self._rounds.append((now_ms, good_round))
                self._enter(self._quality(), ended)
            elif self.state == "down" and self._gateway_fail_streak >= 2:
                self._gateway_down_ms = now_ms
                events.append(self.log.add("gateway_down", now_ms, detail="the router stopped answering"))
                self._enter("lan_down", now_ms)
            elif self.state == "lan_down" and gateway_ok is True:
                started = self._gateway_down_ms if self._gateway_down_ms is not None else now_ms
                events.append(self.log.add("gateway_up", now_ms, outage_s=max(0, round((now_ms - started) / 1000)), detail="the router answers again, the internet still does not"))
                self._gateway_down_ms = None
                self._enter("down", now_ms)
        self.save()
        return events

    def _enter(self, state: str, at_ms: int) -> None:
        self.state, self.since_ms = state, at_ms

    def loss_percent(self) -> float | None:
        if len(self._rounds) < 3:
            return None
        bad = sum(1 for _t, good in self._rounds if not good)
        return round(100.0 * bad / len(self._rounds), 1)

    def _quality(self) -> str:
        """up or degraded, with a margin between going bad and going well so a value on the edge does not flap."""
        loss = self.loss_percent() or 0.0
        latency = self.latency_ms or 0.0
        if self.state == "degraded":
            return "up" if loss < self.recovered_loss and latency < self.recovered_latency else "degraded"
        return "degraded" if loss >= self.degraded_loss or latency >= self.degraded_latency else "up"

    # ---- the picture -------------------------------------------------------------------------------------------------------------------------
    def _trim(self, now_ms: int) -> None:
        self.history = [h for h in self.history if now_ms - h["ended_ms"] <= 7 * DAY_MS][-200:]

    def status(self, now_ms: int) -> dict:
        """The `internet` block of the message."""
        out: dict = {"state": self.state}
        if self.since_ms is not None:
            out["since_ms"] = self.since_ms
        if self.gateway_ok is not None:
            out["gateway_ok"] = self.gateway_ok
        if self.latency_ms is not None:
            out["latency_ms"] = self.latency_ms
        loss = self.loss_percent()
        if loss is not None:
            out["loss_percent"] = loss
        if self.probes:
            out["probes"] = [{"target": p.target[:64], "kind": p.kind, "ok": p.ok, **({"latency_ms": round(p.latency_ms, 1)} if p.latency_ms is not None else {})}
                             for p in self.probes[:8]]
        if self.history:
            last = self.history[-1]
            out["last_outage"] = {"started_ms": last["started_ms"], "ended_ms": last["ended_ms"], "duration_s": max(0, round((last["ended_ms"] - last["started_ms"]) / 1000))}
        since = now_ms - DAY_MS
        began = sum(1 for h in self.history if h["started_ms"] >= since) + (1 if self._outage_start_ms is not None and self._outage_start_ms >= since else 0)
        down_ms = sum(max(0, h["ended_ms"] - max(h["started_ms"], since)) for h in self.history if h["ended_ms"] > since)
        if self._outage_start_ms is not None:
            down_ms += max(0, now_ms - max(self._outage_start_ms, since))
        out["outages_24h"] = began
        out["downtime_24h_s"] = min(86_400, round(down_ms / 1000))
        return out

    # ---- persistence -------------------------------------------------------------------------------------------------------------------------
    def load(self) -> None:
        if self.path is None or not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.history = [{"started_ms": int(h["started_ms"]), "ended_ms": int(h["ended_ms"])} for h in data.get("history", [])]
            ongoing, last = data.get("outage_start_ms"), data.get("last_feed_ms")
            if isinstance(ongoing, int) and isinstance(last, int) and last >= ongoing:
                self.history.append({"started_ms": ongoing, "ended_ms": last})   # the program stopped in the middle of an outage: it counts up to the last thing it knew
        except (OSError, ValueError, KeyError, TypeError):
            self.history = []

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {"version": 1, "history": self.history, "outage_start_ms": self._outage_start_ms, "last_feed_ms": self._last_feed_ms}
        temporary = self.path.with_name(self.path.name + f".{os.getpid()}.tmp")
        temporary.write_text(json.dumps(body, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, self.path)
