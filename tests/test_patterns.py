from discord_username_checker import patterns
from discord_username_checker.patterns import Kind, is_valid


def test_letters_counts():
    assert patterns.letters(3).estimate() == 26 ** 3
    assert patterns.letters(4).estimate() == 26 ** 4


def test_generate_all_valid():
    names = list(patterns.letters(3).generate())
    assert len(names) == 26 ** 3
    assert all(is_valid(n) for n in names)


def test_from_spec_mask():
    p = patterns.from_spec("co??")
    assert p.mask() == "co??"
    assert p.estimate() == 26 * 26


def test_spec_symbols():
    p = patterns.from_spec("?#*%")
    assert [s.kind for s in p.slots] == [Kind.LETTER, Kind.DIGIT, Kind.ALNUM, Kind.FULL]


def test_rules_reject():
    assert not is_valid(".ab")
    assert not is_valid("ab.")
    assert not is_valid("a..b")
    assert not is_valid("a")
    assert not is_valid("a" * 33)
    assert not is_valid("aBc")
    assert is_valid("a.b")
    assert is_valid("a_b")


def test_full_slot_never_leading_or_double_dot():
    p = patterns.from_spec("%b")
    for n in p.generate():
        assert not n.startswith(".")
        assert ".." not in n
