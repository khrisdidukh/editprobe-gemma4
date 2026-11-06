import pytest
from src import parse_color, ColorParseError, ColorTriplet


def test_uppercase_hex():
    assert parse_color("#FF8800") == ("truecolor", None, ColorTriplet(255, 136, 0))


def test_lowercase_hex():
    assert parse_color("#ff8800") == ("truecolor", None, ColorTriplet(255, 136, 0))


def test_standard_and_number():
    assert parse_color("Red") == ("standard", 1, None)
    assert parse_color("color(200)") == ("eight_bit", 200, None)


def test_rgb_and_errors():
    assert parse_color("rgb(1, 2, 3)") == ("truecolor", None, ColorTriplet(1, 2, 3))
    with pytest.raises(ColorParseError):
        parse_color("nope")
    with pytest.raises(ColorParseError):
        parse_color("color(300)")
