from __future__ import annotations

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

            def cb(name, status):
                counts[status] += 1
                progress.advance(task)
                if status is Status.AVAILABLE:
                    out.write(name + "\n")
                    out.flush()
                    progress.console.print(f"  [bold green]free[/]  {name}")
                free = counts[Status.AVAILABLE]
                progress.update(task, description=f"checking  [green]{free} free[/]")

            checker.run(names, cb)
            if checker.interrupted:
                progress.console.print("[yellow]  stopped early, saved what we found[/]")

    return counts


def summary(console, counts, out_path):
    free = counts.get(Status.AVAILABLE, 0)
    taken = counts.get(Status.TAKEN, 0)
    limited = counts.get(Status.RATE_LIMITED, 0)
    blocked = counts.get(Status.BLOCKED, 0)
    errors = counts.get(Status.ERROR, 0)
    console.print()
    console.print(f"  [bold green]{free}[/] free   [dim]{taken} taken[/]")
    if limited or blocked:
        miss = limited + blocked
        console.print(f"  [yellow]{miss} skipped (rate limited / 403) - add residential proxies or lower --workers[/]")
    if errors:
        console.print(f"  [red]{errors} errors[/]")
    if free:
        console.print(f"  saved to [cyan]{out_path}[/]")
    console.print()
