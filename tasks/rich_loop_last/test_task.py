from src import loop_first, loop_last, loop_first_last


def test_loop_last():
    assert list(loop_last([1, 2, 3])) == [(False, 1), (False, 2), (True, 3)]


def test_loop_last_single():
    assert list(loop_last([1])) == [(True, 1)]


def test_loop_first():
    assert list(loop_first("ab")) == [(True, "a"), (False, "b")]


def test_loop_first_last():
    assert list(loop_first_last([1, 2, 3])) == [(True, False, 1), (False, False, 2), (False, True, 3)]
    assert list(loop_first_last([])) == []
