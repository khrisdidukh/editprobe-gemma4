import pytest
from src import check_header_validity, InvalidHeader


def test_leading_space_value_rejected():
    with pytest.raises(InvalidHeader):
        check_header_validity(("X-Test", " value"))


def test_colon_in_value_ok():
    check_header_validity(("Host", "example.com:8080"))


def test_newline_rejected():
    with pytest.raises(InvalidHeader):
        check_header_validity(("X-Test", "a\r\nb"))


def test_bad_name():
    with pytest.raises(InvalidHeader):
        check_header_validity((" X-Test", "v"))
    with pytest.raises(InvalidHeader):
        check_header_validity(("X:Test", "v"))


def test_bytes_ok():
    check_header_validity((b"X-Test", b"v"))
