from __future__ import annotations

import concurrent.futures as cf
import threading
from enum import Enum

import requests

from .proxies import Pool

ENDPOINT = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


class Status(Enum):
    AVAILABLE = "available"
    TAKEN = "taken"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"
    ERROR = "error"


def _ask(session, name, proxy, timeout):
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = session.post(ENDPOINT, json={"username": name}, proxies=proxies, timeout=timeout)
    except requests.RequestException:
        return Status.ERROR, 0.0
    if r.status_code == 200:
        try:
            taken = r.json().get("taken", True)
        except ValueError:
            return Status.ERROR, 0.0
        return (Status.TAKEN if taken else Status.AVAILABLE), 0.0
    if r.status_code == 400:
        # reserved / not allowed (like anything with "discord" in it), can't grab it
        return Status.TAKEN, 0.0
    if r.status_code == 429:
        wait = r.headers.get("retry-after", "1")
        try:
            return Status.RATE_LIMITED, float(wait)
        except ValueError:
            return Status.RATE_LIMITED, 1.0
    if r.status_code == 403:
        return Status.BLOCKED, 0.0
    return Status.ERROR, 0.0


class Checker:
    def __init__(self, proxies=None, workers=8, timeout=10, gap=0.6, max_errors=4):
        self.pool = Pool(proxies, gap=gap)
        self.workers = max(1, workers)
        self.timeout = timeout
        self.max_errors = max_errors
        self.interrupted = False
        self.blocked_out = False
        self._stop = threading.Event()
        self._local = threading.local()

    def stop(self):
        self._stop.set()

    def _session(self):
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update({"user-agent": UA, "content-type": "application/json"})
            self._local.session = s
        return s

    def _check(self, name):
        session = self._session()
        errors = 0
        while not self._stop.is_set():
            lane = self.pool.acquire(self._stop)
            if lane is None:
                return name, Status.RATE_LIMITED
            status, wait = _ask(session, name, lane.url, self.timeout)
            if status is Status.RATE_LIMITED:
                # got rate limited, cool this ip down and try the name again later
                self.pool.penalize(lane, wait)
                continue
            if status is Status.BLOCKED:
                if len(self.pool) == 1:
                    # only got our own ip and discord blocked it, no point going on
                    self.blocked_out = True
                    self._stop.set()
                    return name, Status.BLOCKED
                self.pool.penalize(lane, 60)
                continue
            if status is Status.ERROR:
                errors += 1
                if errors >= self.max_errors:
                    return name, Status.ERROR
                continue
            return name, status
        return name, Status.RATE_LIMITED

    def run(self, names, on_result):
        window = max(self.workers * 4, 16)
        with cf.ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = set()
            try:
                for name in names:
                    if self._stop.is_set():
                        break
                    futures.add(ex.submit(self._check, name))
                    if len(futures) >= window:
                        done, futures = cf.wait(futures, return_when=cf.FIRST_COMPLETED)
                        for fut in done:
                            on_result(*fut.result())
                for fut in cf.as_completed(futures):
                    on_result(*fut.result())
            except KeyboardInterrupt:
                # ctrl-c, stop handing out work and let the running ones die off
                self.interrupted = True
                self._stop.set()
