import pytest
from src import CaseInsensitiveDict


def test_delete_other_case():
    d = CaseInsensitiveDict()
    d["Content-Type"] = "text/html"
    del d["content-type"]
    assert len(d) == 0


def test_delete_same_case():
    d = CaseInsensitiveDict({"Accept": "*/*"})
    del d["Accept"]
    assert "accept" not in d


def test_lookup():
    d = CaseInsensitiveDict({"Accept": "*/*"})
    assert d["ACCEPT"] == "*/*"
    assert list(d) == ["Accept"]


def test_eq():
    assert CaseInsensitiveDict({"a": 1}) == {"A": 1}
