from __future__ import annotations

import concurrent.futures as cf
import threading
from enum import Enum

import requests

from .proxies import Lane, Pool

# no login needed, this is what the signup form uses
API_ENDPOINT = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
# the logged-in "is this name free" check. this ONLY checks, it never changes your
# username (that's a separate PATCH we never make). if discord moved it, override with
# --auth-endpoint. grab the real one from devtools -> network while typing in settings.
AUTH_ENDPOINT = "https://discord.com/api/v9/users/@me/pomelo-attempt"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


class Status(Enum):
    AVAILABLE = "available"
    TAKEN = "taken"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"
    BAD_TOKEN = "bad_token"
    BAD_ENDPOINT = "bad_endpoint"
    ERROR = "error"


def _ask(session, name, lane, timeout, auth_endpoint=AUTH_ENDPOINT):
    proxy = lane.proxy if lane else None
    token = lane.token if lane else None
    url = auth_endpoint if token else API_ENDPOINT
    headers = {"authorization": token} if token else None
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = session.post(url, json={"username": name}, proxies=proxies, timeout=timeout, headers=headers)
    except requests.RequestException:
        return Status.ERROR, 0.0

    code = r.status_code
    if code == 200:
        try:
            data = r.json()
        except ValueError:
            data = {}
        if isinstance(data, dict) and "taken" in data:
            return (Status.TAKEN if data["taken"] else Status.AVAILABLE), 0.0
        return Status.AVAILABLE, 0.0
    if code == 400:
        # reserved / not allowed (like anything with "discord" in it), can't grab it
        return Status.TAKEN, 0.0
    if code in (401, 403) and token:
        return Status.BAD_TOKEN, 0.0
    if code == 403:
        return Status.BLOCKED, 0.0
    if code == 429:
        wait = r.headers.get("retry-after", "1")
        try:
            return Status.RATE_LIMITED, float(wait)
        except ValueError:
            return Status.RATE_LIMITED, 1.0
    if code == 404 and token:
        return Status.BAD_ENDPOINT, 0.0
    return Status.ERROR, 0.0


def build_lanes(mode, proxies, tokens):
    proxies = proxies or []
    if mode == "token":
        lanes = []
        for i, tok in enumerate(tokens or []):
            proxy = proxies[i % len(proxies)] if proxies else None
            lanes.append(Lane(proxy=proxy, token=tok))
        return lanes
    if proxies:
        return [Lane(proxy=p) for p in proxies]
    return [Lane()]


class Checker:
    def __init__(self, mode="api", proxies=None, tokens=None, workers=8, timeout=10,
                 gap=0.6, auth_endpoint=AUTH_ENDPOINT, max_errors=4):
        self.mode = mode
        self.pool = Pool(build_lanes(mode, proxies, tokens), gap=gap)
        self.auth_endpoint = auth_endpoint
        self.workers = max(1, workers)
        self.timeout = timeout
        self.max_errors = max_errors
        self.interrupted = False
        self.blocked_out = False
        self.endpoint_bad = False
        self.bad_tokens = 0
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
                # every lane died (bad tokens), nothing left to check with
                self._stop.set()
                return name, Status.ERROR
            status, wait = _ask(session, name, lane, self.timeout, self.auth_endpoint)
            if status is Status.RATE_LIMITED:
                # cool this ip/account down and try the name again later
                self.pool.penalize(lane, wait)
                continue
            if status is Status.BAD_TOKEN:
                self.pool.kill(lane)
                self.bad_tokens += 1
                continue
            if status is Status.BAD_ENDPOINT:
                self.endpoint_bad = True
                self._stop.set()
                return name, Status.ERROR
            if status is Status.BLOCKED:
                if len(self.pool.alive()) <= 1:
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
