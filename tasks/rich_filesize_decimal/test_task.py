from src import decimal, pick_unit_and_suffix


def test_exact_kb():
    assert decimal(1000) == "1.0 kB"
    assert decimal(1000000) == "1.0 MB"


def test_bytes():
    assert decimal(1) == "1 byte"
    assert decimal(999) == "999 bytes"
    assert decimal(1001) == "1.0 kB"


def test_precision():
    assert decimal(30000, precision=2, separator="") == "30.00kB"


def test_pick_unit():
    assert pick_unit_and_suffix(2500, ["B", "kB", "MB"], 1000) == (1000, "kB")
