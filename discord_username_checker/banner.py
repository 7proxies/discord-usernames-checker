from art import text2art

from . import __version__


def show(console):
    logo = text2art("checker", font="small")
    console.print(logo, style="bold magenta", highlight=False)
    console.print(f"  discord username checker  v{__version__}", style="cyan")
    console.print("  find the 3/4/5 letter names nobody grabbed yet\n", style="dim")
