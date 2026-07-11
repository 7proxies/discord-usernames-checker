import discord_username_checker.checker as checker_mod
from discord_username_checker.checker import Checker, Status, _ask, build_lanes
from discord_username_checker.proxies import Lane


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
        self.last = None

    def post(self, url, **kwargs):
        self.last = (url, kwargs)
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


def test_ask_with_token_sends_auth_header_to_auth_endpoint():
    s = FakeSession(FakeResp(200, {"taken": False}))
    lane = Lane(token="secret-token")
    status, _ = _ask(s, "abc", lane, 10, auth_endpoint="https://auth.example/check")
    assert status is Status.AVAILABLE
    url, kwargs = s.last
    assert url == "https://auth.example/check"
    assert kwargs["headers"]["authorization"] == "secret-token"


def test_ask_bad_token():
    s = FakeSession(FakeResp(401))
    assert _ask(s, "abc", Lane(token="x"), 10)[0] is Status.BAD_TOKEN


def test_ask_bad_endpoint():
    s = FakeSession(FakeResp(404))
    assert _ask(s, "abc", Lane(token="x"), 10)[0] is Status.BAD_ENDPOINT


def test_build_lanes_pairs_tokens_with_proxies():
    lanes = build_lanes("token", ["p1", "p2"], ["t1", "t2", "t3"])
    assert [(ln.token, ln.proxy) for ln in lanes] == [("t1", "p1"), ("t2", "p2"), ("t3", "p1")]


def test_check_waits_then_retries_on_rate_limit(monkeypatch):
    seq = [(Status.RATE_LIMITED, 0.0), (Status.AVAILABLE, 0.0)]
    calls = {"i": 0}

    def fake_ask(session, name, lane, timeout, auth_endpoint=None):
        r = seq[calls["i"]]
        calls["i"] += 1
        return r

    monkeypatch.setattr(checker_mod, "_ask", fake_ask)

    name, status = Checker(workers=1, gap=0.0)._check("abc")
    assert status is Status.AVAILABLE
    assert calls["i"] == 2  # it did not give up, it tried the name again


def test_dead_token_gets_dropped(monkeypatch):
    monkeypatch.setattr(checker_mod, "_ask", lambda *a, **k: (Status.BAD_TOKEN, 0.0))
    ch = Checker(mode="token", tokens=["t1"], workers=1, gap=0.0)
    name, status = ch._check("abc")
    assert status is Status.ERROR
    assert ch.bad_tokens == 1


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
