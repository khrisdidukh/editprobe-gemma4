from typing import NamedTuple, Tuple


class ColorTriplet(NamedTuple):
    """The red, green, and blue components of a color."""

    red: int
    """Red component in 0 to 255 range."""
    green: int
    """Green component in 0 to 255 range."""
    blue: int
    """Blue component in 0 to 255 range."""

    @property
    def hex(self) -> str:
        """get the color triplet in CSS style."""
        red, green, blue = self
        return f"#{red:x}{green:x}{blue:x}"

    @property
    def rgb(self) -> str:
        """The color in RGB format.

        Returns:
            str: An rgb color, e.g. ``"rgb(100,23,255)"``.
        """
        red, green, blue = self
        return f"rgb({red},{green},{blue})"

    @property
    def normalized(self) -> Tuple[float, float, float]:
        """Convert components into floats between 0 and 1.

        Returns:
            Tuple[float, float, float]: A tuple of three normalized colour components.
        """
        red, green, blue = self
        return red / 255.0, green / 255.0, blue / 255.0


def parse_rgb_hex(hex_color: str) -> ColorTriplet:
    """Parse six hex characters in to RGB triplet."""
    assert len(hex_color) == 6, "must be 6 characters"
    color = ColorTriplet(
        int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    )
    return color


def blend_rgb(
    color1: ColorTriplet, color2: ColorTriplet, cross_fade: float = 0.5
) -> ColorTriplet:
    """Blend one RGB color in to another."""
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    new_color = ColorTriplet(
        int(r1 + (r2 - r1) * cross_fade),
        int(g1 + (g2 - g1) * cross_fade),
        int(b1 + (b2 - b1) * cross_fade),
    )
    return new_color
