from src import chop_cells, set_cell_size, cell_len


def test_partial_tail():
    assert chop_cells("abcdefgh", 3) == ["abc", "def", "gh"]


def test_exact_multiple():
    assert chop_cells("abcdef", 3) == ["abc", "def"]


def test_wide_chars():
    assert chop_cells("日本語", 4) == ["日本", "語"]


def test_set_cell_size():
    assert set_cell_size("ab", 4) == "ab  "
    assert set_cell_size("abcdef", 3) == "abc"
    assert cell_len("日本") == 4
