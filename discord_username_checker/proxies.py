from __future__ import annotations

import threading
import time


def normalize(line: str) -> str:
    if "://" in line:
        return line
    parts = line.split(":")
    if len(parts) == 4:
        host, port, user, pw = parts
        return f"http://{user}:{pw}@{host}:{port}"
    # host:port or anything else -> assume http
    return "http://" + line


def load(path: str) -> list[str]:
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.append(normalize(line))
    return out


def load_lines(path: str) -> list[str]:
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


class Lane:
    # one identity that gets rate limited on its own: an exit ip (proxy) and/or an account token
    __slots__ = ("proxy", "token", "until", "last", "dead")

    def __init__(self, proxy=None, token=None):
        self.proxy = proxy
        self.token = token
        self.until = 0.0  # cooling down until this time (after a 429/403)
        self.last = 0.0   # last time we used it, so we can space requests out
        self.dead = False  # token turned out bad, stop using it


class Pool:
    def __init__(self, lanes, gap=0.6):
        self.lanes = lanes if lanes else [Lane()]
        self.gap = gap
        self._lock = threading.Lock()

    def __len__(self):
        return len(self.lanes)

    def alive(self):
        return [ln for ln in self.lanes if not ln.dead]

    def acquire(self, stop):
        # hand out the lane that's ready soonest, waiting if they're all cooling down
        while not stop.is_set():
            with self._lock:
                live = [ln for ln in self.lanes if not ln.dead]
                if not live:
                    return None
                now = time.monotonic()
                lane = min(live, key=lambda ln: max(ln.until, ln.last + self.gap))
                ready_at = max(lane.until, lane.last + self.gap)
                if ready_at <= now:
                    lane.last = now
                    return lane
                wait = ready_at - now
            time.sleep(min(max(wait, 0.02), 0.5))
        return None

    def penalize(self, lane, seconds):
        with self._lock:
            lane.until = max(lane.until, time.monotonic() + seconds)

    def kill(self, lane):
        with self._lock:
            lane.dead = True

    def cooldown(self):
        # seconds until any live lane is free again (0 if one is free now)
        with self._lock:
            live = [ln for ln in self.lanes if not ln.dead]
            if not live:
                return 0.0
            now = time.monotonic()
            return max(0.0, min(ln.until for ln in live) - now)
