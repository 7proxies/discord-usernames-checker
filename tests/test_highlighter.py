from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput

from discord_username_checker import highlighter
from discord_username_checker.patterns import Kind

RIGHT = "\x1b[C"
ESC = "\x1b"
ENTER = "\r"


def run(seed, keys):
    with create_pipe_input() as inp:
        inp.send_text(keys)
        return highlighter.edit(seed, pt_input=inp, pt_output=DummyOutput())


def test_marks_letter_then_digit():
    pat = run("ab", "l" + RIGHT + "d" + ENTER)
    assert pat is not None
    assert [s.kind for s in pat.slots] == [Kind.LETTER, Kind.DIGIT]
    assert pat.mask() == "?#"


def test_fixed_positions_keep_their_char():
    pat = run("cat", "l" + ENTER)
    assert pat.slots[0].kind is Kind.LETTER
    assert pat.slots[1].kind is Kind.FIXED and pat.slots[1].char == "a"
    assert pat.slots[2].kind is Kind.FIXED and pat.slots[2].char == "t"


def test_escape_cancels():
    assert run("ab", ESC) is None
