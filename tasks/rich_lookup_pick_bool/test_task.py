from src import pick_bool, pick_first_str


def test_false_first():
    assert pick_bool(False, True) is False


def test_none_skipped():
    assert pick_bool(None, True) is True
    assert pick_bool(None, None, False) is False


def test_all_none():
    assert pick_bool(None, None) is False


def test_pick_str():
    assert pick_first_str(None, "", "x") == ""
