from src import divide_line, words


def test_exact_fit():
    assert divide_line("foo bar baz", 7) == [8]


def test_basic():
    assert divide_line("foo bar baz", 5) == [4, 8]


def test_no_break():
    assert divide_line("foo bar", 20) == []


def test_fold_long():
    assert divide_line("abcdefghij", 4) == [4, 8]


def test_words():
    assert [w for _, _, w in words("a  bb c")] == ["a  ", "bb ", "c"]
