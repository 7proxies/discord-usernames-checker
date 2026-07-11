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


class Lane:
    # one exit ip (a proxy, or None for your own connection)
    __slots__ = ("url", "until", "last")

    def __init__(self, url):
        self.url = url
        self.until = 0.0  # cooling down until this time (after a 429/403)
        self.last = 0.0   # last time we used it, so we can space requests out


class Pool:
    def __init__(self, proxies, gap=0.6):
        urls = list(proxies) if proxies else [None]
        self.lanes = [Lane(u) for u in urls]
        self.gap = gap
        self._lock = threading.Lock()

    def __len__(self):
        return len(self.lanes)

    def acquire(self, stop):
        # hand out the lane that's ready soonest, waiting if they're all cooling down
        while not stop.is_set():
            with self._lock:
                now = time.monotonic()
                lane = min(self.lanes, key=lambda ln: max(ln.until, ln.last + self.gap))
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

    def cooldown(self):
        # seconds until any lane is free again (0 if one is free now)
        with self._lock:
            now = time.monotonic()
            return max(0.0, min(ln.until for ln in self.lanes) - now)
