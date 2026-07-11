from __future__ import annotations

import argparse
import os
import random
import sys

import questionary
from rich.console import Console

from . import banner, highlighter, patterns
from . import proxies as proxymod
from . import results
from .checker import AUTH_ENDPOINT, Checker

# if a pattern is bigger than this we stream it instead of holding it in memory
CAP = 300_000


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="dusc", description="check which discord usernames are free")
    p.add_argument("--pattern", help="pattern spec, e.g. co?? (? letter, # digit, * letter/digit, %% anything)")
    p.add_argument("--file", help="check usernames from a file, one per line")
    p.add_argument("--three", action="store_true", help="all 3 letter names")
    p.add_argument("--four", action="store_true", help="all 4 letter names")
    p.add_argument("--five", action="store_true", help="all 5 letter names")
    p.add_argument("--proxies", help="path to a proxies file")
    p.add_argument("--token", help="check with one account token (against discord ToS, use an alt)")
    p.add_argument("--tokens", help="file with account tokens, one per line")
    p.add_argument("--auth-endpoint", default=AUTH_ENDPOINT, help="override the token check endpoint")
    p.add_argument("--out", default="available.txt", help="where to save free names")
    p.add_argument("--workers", type=int, default=8, help="how many to check at once")
    p.add_argument("--gap", type=float, default=0.6, help="min seconds between requests per ip (api mode)")
    p.add_argument("--token-gap", type=float, default=3.0, help="min seconds between requests per token")
    p.add_argument("--no-banner", action="store_true", help="skip the ascii art")
    return p.parse_args(argv)


def sanitize(text):
    return "".join(c for c in text.lower() if c in patterns.FULL)[: patterns.MAX_LEN]


def build_names(pattern):
    est = pattern.estimate()
    if est <= CAP:
        names = list(pattern.generate())
        random.shuffle(names)
        return names, len(names)
    return pattern.generate(), est


def load_usernames(path):
    seen = set()
    out = []
    with open(path) as f:
        for line in f:
            n = sanitize(line.strip())
            if n and patterns.is_valid(n) and n not in seen:
                seen.add(n)
                out.append(n)
    return out


def _load_proxies(settings, console):
    path = settings["proxies"]
    if not path:
        return None
    if not os.path.exists(path):
        console.print(f"  [yellow]proxies file not found: {path}[/]")
        return None
    plist = proxymod.load(path)
    console.print(f"  [dim]using {len(plist)} proxies[/]")
    return plist


def _resolve_tokens(settings):
    if settings.get("token_inline"):
        return list(settings["token_inline"])
    path = settings.get("tokens")
    if path and os.path.exists(path):
        return proxymod.load_lines(path)
    return []


def run_names(names, total, settings, console):
    plist = _load_proxies(settings, console)
    mode = settings["mode"]
    tokens = None
    gap = settings["gap"]
    if mode == "token":
        tokens = _resolve_tokens(settings)
        if not tokens:
            console.print("  [red]token mode is on but no tokens are set (settings / --tokens)[/]")
            return
        gap = settings["token_gap"]
        console.print(f"  [dim]using {len(tokens)} account token(s) - hope they're alts[/]")

    checker = Checker(
        mode=mode,
        proxies=plist,
        tokens=tokens,
        workers=settings["workers"],
        gap=gap,
        auth_endpoint=settings["auth_endpoint"],
    )
    counts = results.run(checker, names, total, settings["out"], console)
    results.summary(console, counts, settings["out"], checker)


def run_pattern(pattern, settings, console, ask):
    est = pattern.estimate()
    if est == 0:
        console.print("  [red]that pattern makes no valid names[/]")
        return
    if ask and est > 2000:
        if not questionary.confirm(f"that's about {est:,} names, go?").ask():
            return
    names, total = build_names(pattern)
    run_names(names, total, settings, console)


def run_file(path, settings, console, ask):
    if not os.path.exists(path):
        console.print(f"  [red]no such file: {path}[/]")
        return
    names = load_usernames(path)
    if not names:
        console.print("  [yellow]no valid usernames in that file[/]")
        return
    console.print(f"  [dim]loaded {len(names):,} names from {path}[/]")
    if ask and len(names) > 2000:
        if not questionary.confirm(f"that's {len(names):,} names, go?").ask():
            return
    run_names(names, len(names), settings, console)


def ask_pattern(console):
    seed = questionary.text("type a base word (only a-z 0-9 . _):").ask()
    if not seed:
        return None
    seed = sanitize(seed)
    if not seed:
        console.print("  [red]nothing usable in there[/]")
        return None
    pat = highlighter.edit(seed)
    if pat is None:
        return None
    console.print(f"  pattern: [cyan]{pat.mask()}[/]")
    return pat


TOKEN_CHOICE = "account tokens (recommended)"
API_CHOICE = "discord api (no login)"


def _enable_token_mode(settings, console):
    console.print("[yellow]  heads up: using account tokens is self-botting and can get the[/yellow]")
    console.print("[yellow]  account banned. use throwaway accounts only.[/yellow]")
    if not questionary.confirm("ok with that?").ask():
        settings["mode"] = "api"
        return
    settings["mode"] = "token"
    toks = questionary.text("tokens file:", default=settings.get("tokens") or "tokens.txt").ask()
    settings["tokens"] = toks or "tokens.txt"
    gap = questionary.text("min seconds between requests per token:", default=str(settings["token_gap"])).ask()
    try:
        settings["token_gap"] = max(0.0, float(gap))
    except (TypeError, ValueError):
        pass


def choose_mode(settings, console):
    pick = questionary.select(
        "how do you want to check?",
        choices=[TOKEN_CHOICE, API_CHOICE],
    ).ask()
    if pick == TOKEN_CHOICE:
        _enable_token_mode(settings, console)
    else:
        settings["mode"] = "api"


def edit_settings(settings, console):
    pick = questionary.select(
        "check via:",
        choices=[TOKEN_CHOICE, API_CHOICE],
        default=TOKEN_CHOICE if settings["mode"] == "token" else API_CHOICE,
    ).ask()
    if pick == TOKEN_CHOICE:
        _enable_token_mode(settings, console)
    else:
        settings["mode"] = "api"

    proxies = questionary.text("proxies file (blank = none):", default=settings["proxies"] or "").ask()
    settings["proxies"] = proxies or None
    workers = questionary.text("workers:", default=str(settings["workers"])).ask()
    if workers and workers.isdigit():
        settings["workers"] = max(1, int(workers))
    out = questionary.text("save free names to:", default=settings["out"]).ask()
    if out:
        settings["out"] = out


def interactive(settings, console):
    while True:
        tag = "  [magenta](token mode)[/]" if settings["mode"] == "token" else ""
        if tag:
            console.print(tag)
        choice = questionary.select(
            "what do you want to check?",
            choices=[
                "3 letter names",
                "4 letter names",
                "5 letter names",
                "custom pattern",
                "check from a file",
                "settings",
                "quit",
            ],
        ).ask()
        if not choice or choice == "quit":
            console.print("  bye")
            return
        try:
            if choice == "settings":
                edit_settings(settings, console)
                continue
            if choice == "check from a file":
                path = questionary.text("file with usernames (one per line):").ask()
                if path:
                    run_file(path, settings, console, ask=True)
                continue
            if choice == "custom pattern":
                pat = ask_pattern(console)
                if pat is None:
                    continue
            else:
                pat = patterns.letters(int(choice[0]))
            run_pattern(pat, settings, console, ask=True)
        except KeyboardInterrupt:
            console.print("\n  stopped")
        except Exception as e:
            console.print(f"  oops: {e}", markup=False, style="red")


def main():
    args = parse_args()
    console = Console()
    if not args.no_banner:
        banner.show(console)

    settings = {
        "workers": args.workers,
        "proxies": args.proxies,
        "out": args.out,
        "gap": args.gap,
        "token_gap": args.token_gap,
        "auth_endpoint": args.auth_endpoint,
        "mode": "api",
        "tokens": args.tokens,
        "token_inline": [args.token] if args.token else None,
    }
    if not settings["proxies"] and os.path.exists("proxies.txt"):
        settings["proxies"] = "proxies.txt"
    if args.token or args.tokens:
        settings["mode"] = "token"
    elif not settings["tokens"] and os.path.exists("tokens.txt"):
        settings["tokens"] = "tokens.txt"

    if args.file:
        run_file(args.file, settings, console, ask=False)
        return

    pat = None
    if args.pattern:
        pat = patterns.from_spec(args.pattern)
    elif args.three:
        pat = patterns.letters(3)
    elif args.four:
        pat = patterns.letters(4)
    elif args.five:
        pat = patterns.letters(5)

    if pat is not None:
        run_pattern(pat, settings, console, ask=False)
        return

    if not sys.stdin.isatty():
        console.print("  the menu needs a real terminal. or use flags like --three / --file / --pattern.")
        return
    try:
        if not (args.token or args.tokens):
            # ask up front, token mode is the recommended default
            choose_mode(settings, console)
        interactive(settings, console)
    except KeyboardInterrupt:
        console.print("\n  bye")
