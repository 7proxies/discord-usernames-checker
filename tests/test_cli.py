import io

from rich.console import Console

import discord_username_checker.cli as cli


class FakeQ:
    def __init__(self, value):
        self._v = value

    def ask(self):
        return self._v


def _console():
    return Console(file=io.StringIO())


def _settings():
    return {
        "workers": 8,
        "proxies": None,
        "out": "available.txt",
        "gap": 0.6,
        "token_gap": 3.0,
        "auth_endpoint": "x",
        "mode": "api",
        "tokens": None,
        "token_inline": None,
    }


def test_choose_mode_token(monkeypatch):
    monkeypatch.setattr(cli.questionary, "select", lambda *a, **k: FakeQ(cli.TOKEN_CHOICE))
    monkeypatch.setattr(cli.questionary, "confirm", lambda *a, **k: FakeQ(True))
    monkeypatch.setattr(cli.questionary, "text", lambda *a, **k: FakeQ(""))
    s = _settings()
    cli.choose_mode(s, _console())
    assert s["mode"] == "token"
    assert s["tokens"] == "tokens.txt"


def test_choose_mode_api(monkeypatch):
    monkeypatch.setattr(cli.questionary, "select", lambda *a, **k: FakeQ(cli.API_CHOICE))
    s = _settings()
    cli.choose_mode(s, _console())
    assert s["mode"] == "api"


def test_declining_the_warning_falls_back_to_api(monkeypatch):
    monkeypatch.setattr(cli.questionary, "select", lambda *a, **k: FakeQ(cli.TOKEN_CHOICE))
    monkeypatch.setattr(cli.questionary, "confirm", lambda *a, **k: FakeQ(False))
    s = _settings()
    cli.choose_mode(s, _console())
    assert s["mode"] == "api"


def test_resolve_proxies_mullvad(monkeypatch):
    monkeypatch.setattr(cli.mullvad, "is_connected", lambda *a, **k: True)
    monkeypatch.setattr(cli.mullvad, "fetch_proxies", lambda *a, **k: ["socks5h://x:1080"])
    s = _settings()
    s["mullvad"] = True
    assert cli.resolve_proxies(s, _console(), ask=False) == ["socks5h://x:1080"]


def test_resolve_proxies_no_proxy_warns_and_continues():
    s = _settings()
    assert cli.resolve_proxies(s, _console(), ask=False) is None
    assert s["proxy_ack"] is True


def test_resolve_proxies_asks_and_loads(monkeypatch, tmp_path):
    p = tmp_path / "p.txt"
    p.write_text("1.2.3.4:8080\n")
    monkeypatch.setattr(cli.sys, "stdin", type("S", (), {"isatty": lambda self: True})())
    monkeypatch.setattr(cli.questionary, "text", lambda *a, **k: FakeQ(str(p)))
    s = _settings()
    assert cli.resolve_proxies(s, _console(), ask=True) == ["http://1.2.3.4:8080"]
    assert s["proxies"] == str(p)
