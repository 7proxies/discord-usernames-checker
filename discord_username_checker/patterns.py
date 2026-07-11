from __future__ import annotations

import itertools
import string
from dataclasses import dataclass, field
from enum import Enum

# what discord actually allows in the new username system
LETTERS = string.ascii_lowercase
DIGITS = string.digits
ALNUM = LETTERS + DIGITS
FULL = ALNUM + "._"

MIN_LEN = 2
MAX_LEN = 32


class Kind(Enum):
    FIXED = "fixed"
    LETTER = "letter"
    DIGIT = "digit"
    ALNUM = "alnum"
    FULL = "full"


CHARSETS = {
    Kind.LETTER: LETTERS,
    Kind.DIGIT: DIGITS,
    Kind.ALNUM: ALNUM,
    Kind.FULL: FULL,
}

# short marks used when we print a wildcard slot
MARK = {Kind.LETTER: "?", Kind.DIGIT: "#", Kind.ALNUM: "*", Kind.FULL: "%"}
SYMBOLS = {v: k for k, v in MARK.items()}


@dataclass
class Slot:
    kind: Kind
    char: str = ""

    def choices(self) -> str:
        if self.kind is Kind.FIXED:
            return self.char
        return CHARSETS[self.kind]

    def show(self) -> str:
        return self.char if self.kind is Kind.FIXED else MARK[self.kind]


@dataclass
class Pattern:
    slots: list[Slot] = field(default_factory=list)

    def estimate(self) -> int:
        # upper bound, the dot rules drop a few of these
        n = 1
        for s in self.slots:
            n *= len(s.choices())
        return n

    def mask(self) -> str:
        return "".join(s.show() for s in self.slots)

    def generate(self):
        pools = [s.choices() for s in self.slots]
        for combo in itertools.product(*pools):
            name = "".join(combo)
            if is_valid(name):
                yield name


def is_valid(name: str) -> bool:
    if not MIN_LEN <= len(name) <= MAX_LEN:
        return False
    if name[0] == "." or name[-1] == ".":
        return False
    if ".." in name:
        return False
    return all(c in FULL for c in name)


def letters(n: int) -> Pattern:
    return Pattern([Slot(Kind.LETTER) for _ in range(n)])


def from_spec(spec: str) -> Pattern:
    # tiny language for the --pattern flag: ? letter, # digit, * letter/digit, % anything
    slots = []
    for ch in spec.lower():
        if ch in SYMBOLS:
            slots.append(Slot(SYMBOLS[ch]))
        else:
            slots.append(Slot(Kind.FIXED, ch))
    return Pattern(slots)
