import re
from typing import NamedTuple, Optional, Tuple


class ColorParseError(Exception):
    """The color could not be parsed."""


class ColorTriplet(NamedTuple):
    red: int
    green: int
    blue: int


RE_COLOR = re.compile(
    r"""^
\#([0-9a-f]{6})$|
color\(([0-9]{1,3})\)$|
rgb\(([\d\s,]+)\)$
""",
    re.VERBOSE | re.IGNORECASE,
)

STANDARD = {"black": 0, "red": 1, "green": 2, "yellow": 3, "blue": 4, "magenta": 5, "cyan": 6, "white": 7}


def parse_rgb_hex(hex_color: str) -> ColorTriplet:
    """Parse six hex characters in to RGB triplet."""
    assert len(hex_color) == 6, "must be 6 characters"
    return ColorTriplet(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def parse_color(color: str) -> Tuple[str, Optional[int], Optional[ColorTriplet]]:
    """Parse a color definition.

    Returns a tuple of (kind, number, triplet) where kind is one of
    "standard", "eight_bit" or "truecolor".
    """
    original_color = color
    color = color.strip()

    if color in STANDARD:
        return "standard", STANDARD[color], None

    color_match = RE_COLOR.match(color)
    if color_match is None:
        raise ColorParseError(f"{original_color!r} is not a valid color")

    color_24, color_8, color_rgb = color_match.groups()
    if color_24:
        return "truecolor", None, parse_rgb_hex(color_24)

    elif color_8:
        number = int(color_8)
        if number > 255:
            raise ColorParseError(f"color number must be <= 255 in {original_color!r}")
        return "eight_bit", number, None

    else:  # color_rgb:
        components = color_rgb.split(",")
        if len(components) != 3:
            raise ColorParseError(f"expected three components in {original_color!r}")
        red, green, blue = components
        triplet = ColorTriplet(int(red), int(green), int(blue))
        if not all(component <= 255 for component in triplet):
            raise ColorParseError(f"color components must be <= 255 in {original_color!r}")
        return "truecolor", None, triplet
