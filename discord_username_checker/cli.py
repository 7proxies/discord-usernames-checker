from __future__ import annotations

import argparse
import os
import random

import questionary
from rich.console import Console

from . import banner, highlighter, patterns
from . import proxies as proxymod
from . import results
from .checker import Checker

# if a pattern is bigger than this we stream it instead of holding it in memory
CAP = 300_000


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="dusc", description="check which discord usernames are free")
    p.add_argument("--pattern", help="pattern spec, e.g. co?? (? letter, # digit, * letter/digit, %% anything)")
    p.add_argument("--three", action="store_true", help="all 3 letter names")
    p.add_argument("--four", action="store_true", help="all 4 letter names")
    p.add_argument("--five", action="store_true", help="all 5 letter names")
    p.add_argument("--proxies", help="path to a proxies file")
    p.add_argument("--out", default="available.txt", help="where to save free names")
    p.add_argument("--workers", type=int, default=8, help="how many to check at once")
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


def do_run(pattern, settings, console, ask):
    est = pattern.estimate()
    if est == 0:
        console.print("  [red]that pattern makes no valid names[/]")
        return
    if ask and est > 2000:
        if not questionary.confirm(f"that's about {est:,} names, go?").ask():
            return

    pool = None
    proxy_path = settings["proxies"]
    if proxy_path:
        if os.path.exists(proxy_path):
            plist = proxymod.load(proxy_path)
            pool = proxymod.Pool(plist)
            console.print(f"  [dim]using {len(plist)} proxies[/]")
        else:
            console.print(f"  [yellow]proxies file not found: {proxy_path}[/]")

    names, total = build_names(pattern)
    checker = Checker(proxy_pool=pool, workers=settings["workers"])
    counts = results.run(checker, names, total, settings["out"], console)
    results.summary(console, counts, settings["out"])


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


def edit_settings(settings, console):
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
        choice = questionary.select(
            "what do you want to check?",
            choices=[
                "3 letter names",
                "4 letter names",
                "5 letter names",
                "custom pattern",
                "settings",
                "quit",
            ],
        ).ask()
        if not choice or choice == "quit":
            console.print("  bye")
            return
        if choice == "settings":
            edit_settings(settings, console)
            continue
        if choice == "custom pattern":
            pat = ask_pattern(console)
            if pat is None:
                continue
        else:
            pat = patterns.letters(int(choice[0]))
        do_run(pat, settings, console, ask=True)


def main():
    args = parse_args()
    console = Console()
    if not args.no_banner:
        banner.show(console)

    settings = {"workers": args.workers, "proxies": args.proxies, "out": args.out}
    if not settings["proxies"] and os.path.exists("proxies.txt"):
        settings["proxies"] = "proxies.txt"

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
        do_run(pat, settings, console, ask=False)
        return

    interactive(settings, console)
