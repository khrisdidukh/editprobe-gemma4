import pytest
from src import iter_slices, to_key_val_list


def test_tail_kept():
    assert list(iter_slices("abcdefg", 3)) == ["abc", "def", "g"]


def test_exact():
    assert list(iter_slices("abcdef", 3)) == ["abc", "def"]


def test_none_length():
    assert list(iter_slices("abc", None)) == ["abc"]


def test_key_val_list():
    assert to_key_val_list({"k": "v"}) == [("k", "v")]
    with pytest.raises(ValueError):
        to_key_val_list("string")
