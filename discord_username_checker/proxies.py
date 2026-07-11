from __future__ import annotations

import itertools
import threading


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


class Pool:
    def __init__(self, proxies: list[str]):
        self.proxies = proxies
        self._cycle = itertools.cycle(proxies) if proxies else None
        self._lock = threading.Lock()

    def next(self):
        if not self.proxies:
            return None
        with self._lock:
            return next(self._cycle)

    def __len__(self):
        return len(self.proxies)

    def __bool__(self):
        return bool(self.proxies)
