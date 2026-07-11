import discord_username_checker.checker as checker_mod
from discord_username_checker.checker import Checker, Status, _ask


class FakeResp:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    def __init__(self, resp):
        self.resp = resp

    def post(self, *a, **k):
        return self.resp


def test_ask_available():
    s = FakeSession(FakeResp(200, {"taken": False}))
    assert _ask(s, "abc", None, 10) == (Status.AVAILABLE, 0.0)


def test_ask_taken():
    s = FakeSession(FakeResp(200, {"taken": True}))
    assert _ask(s, "abc", None, 10)[0] is Status.TAKEN


def test_ask_400_counts_as_taken():
    s = FakeSession(FakeResp(400, {"message": "nope"}))
    assert _ask(s, "discordx", None, 10)[0] is Status.TAKEN


def test_ask_429_returns_retry_after():
    s = FakeSession(FakeResp(429, None, {"retry-after": "2.5"}))
    status, wait = _ask(s, "abc", None, 10)
    assert status is Status.RATE_LIMITED
    assert wait == 2.5


def test_ask_403_blocked():
    s = FakeSession(FakeResp(403))
    assert _ask(s, "abc", None, 10)[0] is Status.BLOCKED


def test_check_waits_then_retries_on_rate_limit(monkeypatch):
    seq = [(Status.RATE_LIMITED, 0.0), (Status.AVAILABLE, 0.0)]
    calls = {"i": 0}

    def fake_ask(session, name, proxy, timeout):
        r = seq[calls["i"]]
        calls["i"] += 1
        return r

    monkeypatch.setattr(checker_mod, "_ask", fake_ask)

    name, status = Checker(workers=1, gap=0.0)._check("abc")
    assert status is Status.AVAILABLE
    assert calls["i"] == 2  # it did not give up, it tried the name again


def test_single_ip_block_stops(monkeypatch):
    monkeypatch.setattr(checker_mod, "_ask", lambda *a, **k: (Status.BLOCKED, 0.0))
    ch = Checker(workers=1, gap=0.0)
    name, status = ch._check("abc")
    assert status is Status.BLOCKED
    assert ch.blocked_out is True


def test_run_collects_every_name(monkeypatch):
    monkeypatch.setattr(checker_mod, "_ask", lambda *a, **k: (Status.AVAILABLE, 0.0))
    got = []
    Checker(workers=3, gap=0.0).run(iter(["aaa", "bbb", "ccc", "ddd"]), lambda n, s: got.append((n, s)))
    assert sorted(n for n, _ in got) == ["aaa", "bbb", "ccc", "ddd"]
    assert all(s is Status.AVAILABLE for _, s in got)
