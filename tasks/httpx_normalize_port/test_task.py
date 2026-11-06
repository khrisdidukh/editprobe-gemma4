import pytest
from src import normalize_port, port_or_default, InvalidURL


def test_https_default_removed():
    assert normalize_port("443", "https") is None
    assert normalize_port(443, "wss") is None


def test_http_default_removed():
    assert normalize_port("80", "http") is None


def test_non_default_kept():
    assert normalize_port("8443", "https") == 8443
    assert normalize_port("", "https") is None


def test_invalid():
    with pytest.raises(InvalidURL):
        normalize_port("abc", "http")


def test_port_or_default():
    assert port_or_default("https", None) == 443
    assert port_or_default("http", 8080) == 8080
