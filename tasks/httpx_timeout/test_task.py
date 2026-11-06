import pytest
from src import Timeout


def test_default_applies_to_read():
    t = Timeout(10.0, connect=5.0)
    assert t.as_dict() == {"connect": 5.0, "read": 10.0, "write": 10.0, "pool": 10.0}


def test_single_value():
    assert Timeout(5.0).as_dict() == {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0}
    assert repr(Timeout(5.0)) == "Timeout(timeout=5.0)"


def test_none_default():
    assert Timeout(None, connect=5.0).read is None


def test_errors_and_copy():
    with pytest.raises(ValueError):
        Timeout(connect=1.0)
    assert Timeout(Timeout(3.0)) == Timeout(3.0)
