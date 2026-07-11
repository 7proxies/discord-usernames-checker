from __future__ import annotations

import threading
from collections import Counter

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .checker import Status


def run(checker, names, total, out_path, console):
    counts = Counter()
    columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
    ]
    with open(out_path, "a") as out:
        with Progress(*columns, console=console) as progress:
            task = progress.add_task("checking", total=total)

            def describe():
                free = counts[Status.AVAILABLE]
                cd = checker.pool.cooldown()
                if cd > 1:
                    return f"[yellow]cooling down {int(cd)}s[/]  [green]{free} free[/]"
                return f"checking  [green]{free} free[/]"

            # small thread just to keep the cooldown countdown moving while we wait
            ticking = threading.Event()

            def tick():
                while not ticking.is_set():
                    progress.update(task, description=describe())
                    ticking.wait(0.5)

            ticker = threading.Thread(target=tick, daemon=True)
            ticker.start()

            def cb(name, status):
                counts[status] += 1
                progress.advance(task)
                if status is Status.AVAILABLE:
                    out.write(name + "\n")
                    out.flush()
                    progress.console.print(f"  [bold green]free[/]  {name}")
                progress.update(task, description=describe())

            checker.run(names, cb)
            ticking.set()
            if checker.interrupted:
                progress.console.print("[yellow]  stopped early, saved what we found[/]")

    return counts


def summary(console, counts, out_path, checker=None):
    free = counts.get(Status.AVAILABLE, 0)
    taken = counts.get(Status.TAKEN, 0)
    limited = counts.get(Status.RATE_LIMITED, 0)
    errors = counts.get(Status.ERROR, 0)
    console.print()
    console.print(f"  [bold green]{free}[/] free   [dim]{taken} taken[/]")
    if checker is not None and checker.blocked_out:
        console.print("  [red]your ip got blocked (403) - add proxies and try again[/]")
    if limited:
        console.print(f"  [yellow]{limited} left unchecked (stopped while rate limited)[/]")
    if errors:
        console.print(f"  [red]{errors} errors[/]")
    if free:
        console.print(f"  saved to [cyan]{out_path}[/]")
    console.print()
