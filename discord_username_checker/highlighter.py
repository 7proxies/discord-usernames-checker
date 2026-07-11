from __future__ import annotations

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.styles import Style

from .patterns import CHARSETS, Kind, Pattern, Slot

# order we cycle through when you press up/down or space
CYCLE = [Kind.FIXED, Kind.LETTER, Kind.DIGIT, Kind.ALNUM, Kind.FULL]

STYLE_FOR = {
    Kind.FIXED: "fixed",
    Kind.LETTER: "letter",
    Kind.DIGIT: "digit",
    Kind.ALNUM: "alnum",
    Kind.FULL: "full",
}

HOTKEYS = {
    "f": Kind.FIXED,
    "l": Kind.LETTER,
    "d": Kind.DIGIT,
    "n": Kind.ALNUM,
    "u": Kind.FULL,
}

_STYLE = Style.from_dict(
    {
        "fixed": "#9ca3af",
        "letter": "#22d3ee bold",
        "digit": "#eab308 bold",
        "alnum": "#22c55e bold",
        "full": "#d946ef bold",
        "dim": "#6b7280",
        "title": "#e5e7eb bold",
    }
)


def _sample(slots):
    out = []
    for s in slots:
        out.append(s.char if s.kind is Kind.FIXED else CHARSETS[s.kind][0])
    return "".join(out)


def edit(seed: str, pt_input=None, pt_output=None):
    seed = seed.lower()
    if not seed:
        return None
    slots = [Slot(Kind.FIXED, c) for c in seed]
    cursor = {"i": 0}
    picked = {"pattern": None}

    def cycle(step):
        s = slots[cursor["i"]]
        s.kind = CYCLE[(CYCLE.index(s.kind) + step) % len(CYCLE)]

    def render():
        out = [("class:title", "\n  build your pattern\n\n   ")]
        for i, s in enumerate(slots):
            style = "class:" + STYLE_FOR[s.kind]
            if i == cursor["i"]:
                style += " reverse"
            out.append((style, f" {s.show()} "))
        pat = Pattern(slots)
        out.append(("", "\n\n"))
        out.append(("class:dim", "   move "))
        out.append(("", "<- ->   "))
        out.append(("class:dim", "change "))
        out.append(("", "up/down/space   "))
        out.append(("class:dim", "go "))
        out.append(("", "enter   "))
        out.append(("class:dim", "cancel "))
        out.append(("", "esc\n   "))
        out.append(("class:letter", "l letter  "))
        out.append(("class:digit", "d digit  "))
        out.append(("class:alnum", "n letter+digit  "))
        out.append(("class:full", "u any (._)  "))
        out.append(("class:fixed", "f fixed"))
        out.append(("", "\n\n"))
        out.append(("class:dim", f"   combos ~ {pat.estimate():,}   example: "))
        out.append(("class:letter", _sample(slots)))
        out.append(("", "\n"))
        return out

    kb = KeyBindings()

    @kb.add("left")
    def _(event):
        cursor["i"] = max(0, cursor["i"] - 1)

    @kb.add("right")
    def _(event):
        cursor["i"] = min(len(slots) - 1, cursor["i"] + 1)

    @kb.add("up")
    @kb.add(" ")
    def _(event):
        cycle(1)

    @kb.add("down")
    def _(event):
        cycle(-1)

    for key, kind in HOTKEYS.items():
        @kb.add(key)
        def _(event, kind=kind):
            slots[cursor["i"]].kind = kind

    @kb.add("enter")
    def _(event):
        picked["pattern"] = Pattern([Slot(s.kind, s.char) for s in slots])
        event.app.exit()

    @kb.add("escape")
    @kb.add("c-c")
    @kb.add("q")
    def _(event):
        event.app.exit()

    control = FormattedTextControl(render, focusable=True, show_cursor=False)
    window = Window(control, height=Dimension(min=10), always_hide_cursor=True)
    app = Application(
        layout=Layout(window),
        key_bindings=kb,
        style=_STYLE,
        full_screen=False,
        input=pt_input,
        output=pt_output,
    )
    app.run()
    return picked["pattern"]
