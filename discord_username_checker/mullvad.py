from __future__ import annotations

import requests

# public relay list, reachable connected or not
RELAYS_URL = "https://api.mullvad.net/app/v1/relays"
# tells you if you're actually tunneled through mullvad right now
CONNECTED_URL = "https://am.i.mullvad.net/connected"
SOCKS_PORT = 1080


def socks_host(hostname: str) -> str:
    # wireguard relay "nl-ams-wg-001" exposes its socks proxy as
    # "nl-ams-wg-socks5-001.relays.mullvad.net" (reachable from inside the tunnel)
    prefix, _, num = hostname.rpartition("-")
    if not prefix or not num:
        return f"{hostname}.relays.mullvad.net"
    return f"{prefix}-socks5-{num}.relays.mullvad.net"


def fetch_proxies(timeout: int = 10) -> list[str]:
    # every active wireguard relay = one socks5 exit ip. socks5h so dns for
    # discord.com is resolved at the exit, not locally.
    r = requests.get(RELAYS_URL, timeout=timeout)
    r.raise_for_status()
    relays = r.json().get("wireguard", {}).get("relays", [])
    out = []
    for relay in relays:
        if not relay.get("active"):
            continue
        host = relay.get("hostname")
        if host:
            out.append(f"socks5h://{socks_host(host)}:{SOCKS_PORT}")
    return out


def is_connected(timeout: int = 5) -> bool:
    try:
        r = requests.get(CONNECTED_URL, timeout=timeout)
        return "You are connected" in r.text
    except requests.RequestException:
        return False
