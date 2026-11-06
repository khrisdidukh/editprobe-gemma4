from src import ColorTriplet, parse_rgb_hex, blend_rgb


def test_hex_padding():
    assert ColorTriplet(0, 128, 255).hex == "#0080ff"
    assert ColorTriplet(1, 2, 3).hex == "#010203"


def test_hex_plain():
    assert ColorTriplet(255, 255, 255).hex == "#ffffff"


def test_rgb_normalized():
    t = ColorTriplet(255, 0, 51)
    assert t.rgb == "rgb(255,0,51)"
    assert t.normalized == (1.0, 0.0, 0.2)


def test_parse_blend():
    assert parse_rgb_hex("0080ff") == ColorTriplet(0, 128, 255)
    assert blend_rgb(ColorTriplet(0, 0, 0), ColorTriplet(100, 100, 100)) == ColorTriplet(50, 50, 50)
