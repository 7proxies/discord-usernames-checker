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
