import pytest
from src import parse_dict_header


def test_value_with_equals():
    assert parse_dict_header('token="abc=="') == {"token": "abc=="}


def test_plain():
    d = parse_dict_header('foo="is a fish", bar="as well"')
    assert sorted(d.items()) == [("bar", "as well"), ("foo", "is a fish")]


def test_no_value():
    assert parse_dict_header("key_without_value") == {"key_without_value": None}


def test_unquoted_equals():
    assert parse_dict_header("a=b=c") == {"a": "b=c"}
