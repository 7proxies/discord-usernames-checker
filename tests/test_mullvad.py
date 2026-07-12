import discord_username_checker.mullvad as mullvad


class FakeResp:
    def __init__(self, payload=None, text=""):
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_socks_host():
    assert mullvad.socks_host("nl-ams-wg-001") == "nl-ams-wg-socks5-001.relays.mullvad.net"
    assert mullvad.socks_host("us-nyc-wg-301") == "us-nyc-wg-socks5-301.relays.mullvad.net"


def test_fetch_proxies_skips_inactive(monkeypatch):
    payload = {"wireguard": {"relays": [
        {"hostname": "se-got-wg-001", "active": True},
        {"hostname": "de-fra-wg-002", "active": False},
        {"hostname": "us-nyc-wg-003", "active": True},
    ]}}
    monkeypatch.setattr(mullvad.requests, "get", lambda *a, **k: FakeResp(payload))
    assert mullvad.fetch_proxies() == [
        "socks5h://se-got-wg-socks5-001.relays.mullvad.net:1080",
        "socks5h://us-nyc-wg-socks5-003.relays.mullvad.net:1080",
    ]


def test_is_connected(monkeypatch):
    monkeypatch.setattr(mullvad.requests, "get", lambda *a, **k: FakeResp(text="You are connected to Mullvad"))
    assert mullvad.is_connected() is True
    monkeypatch.setattr(mullvad.requests, "get", lambda *a, **k: FakeResp(text="You are not connected"))
    assert mullvad.is_connected() is False
