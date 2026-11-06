"""Tasks adapted from Textualize/rich (MIT). Standalone modules; see tasks_requests.py."""

TASKS = []


def task(**kw):
    TASKS.append(kw)


# ---------------------------------------------------------------------------
task(
    id="rich_loop_last",
    source="rich/_loop.py::loop_last",
    problem_statement="""loop_last never flags the last element

```python
>>> list(loop_last([1, 2, 3]))
[(False, 1), (False, 2), (False, 3)]
```

The last tuple should be `(True, 3)`. `loop_first` works. Table borders that depend on this draw the row separator after the final row.
""",
    gold='''from typing import Iterable, Tuple, TypeVar

T = TypeVar("T")


def loop_first(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for first value."""
    iter_values = iter(values)
    try:
        value = next(iter_values)
    except StopIteration:
        return
    yield True, value
    for value in iter_values:
        yield False, value


def loop_last(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value


def loop_first_last(values: Iterable[T]) -> Iterable[Tuple[bool, bool, T]]:
    """Iterate and generate a tuple with a flag for first and last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    first = True
    for value in iter_values:
        yield first, False, previous_value
        first = False
        previous_value = value
    yield first, True, previous_value
''',
    mutation=(
        "        previous_value = value\n    yield True, previous_value\n\n\ndef loop_first_last",
        "        previous_value = value\n    yield False, previous_value\n\n\ndef loop_first_last",
    ),
    tests='''from src import loop_first, loop_last, loop_first_last


def test_loop_last():
    assert list(loop_last([1, 2, 3])) == [(False, 1), (False, 2), (True, 3)]


def test_loop_last_single():
    assert list(loop_last([1])) == [(True, 1)]


def test_loop_first():
    assert list(loop_first("ab")) == [(True, "a"), (False, "b")]


def test_loop_first_last():
    assert list(loop_first_last([1, 2, 3])) == [(True, False, 1), (False, False, 2), (False, True, 3)]
    assert list(loop_first_last([])) == []
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_ratio_distribute",
    source="rich/_ratio.py::ratio_distribute",
    problem_statement="""ratio_distribute does not respect minimums

```python
>>> ratio_distribute(10, [1, 1], minimums=[8, 1])
[5, 5]
```

The first column has a minimum of 8, so I expect `[8, 2]`. Without minimums the split is fine.
""",
    gold='''from fractions import Fraction
from math import ceil
from typing import List, Optional


def ratio_distribute(
    total: int, ratios: List[int], minimums: Optional[List[int]] = None
) -> List[int]:
    """Distribute an integer total in to parts based on ratios.

    Args:
        total (int): The total to divide.
        ratios (List[int]): A list of integer ratios.
        minimums (List[int]): List of minimum values for each slot.

    Returns:
        List[int]: A list of integers guaranteed to sum to total.
    """
    if minimums:
        ratios = [ratio if _min else 0 for ratio, _min in zip(ratios, minimums)]
    total_ratio = sum(ratios)
    assert total_ratio > 0, "Sum of ratios must be > 0"

    total_remaining = total
    distributed_total: List[int] = []
    if minimums is None:
        _minimums = [0] * len(ratios)
    else:
        _minimums = minimums
    for ratio, minimum in zip(ratios, _minimums):
        if total_ratio > 0:
            distributed = max(minimum, ceil(ratio * total_remaining / total_ratio))
        else:
            distributed = total_remaining
        distributed_total.append(distributed)
        total_ratio -= ratio
        total_remaining -= distributed
    return distributed_total


def ratio_reduce(
    total: int, ratios: List[int], maximums: List[int], values: List[int]
) -> List[int]:
    """Divide an integer total in to parts based on ratios.

    Args:
        total (int): The total to divide.
        ratios (List[int]): A list of integer ratios.
        maximums (List[int]): List of maximums values for each slot.
        values (List[int]): List of values

    Returns:
        List[int]: A list of integers guaranteed to sum to total.
    """
    ratios = [ratio if _max else 0 for ratio, _max in zip(ratios, maximums)]
    total_ratio = sum(ratios)
    if not total_ratio:
        return values[:]
    total_remaining = total
    result: List[int] = []
    append = result.append
    for ratio, maximum, value in zip(ratios, maximums, values):
        if ratio and total_ratio > 0:
            distributed = min(maximum, round(ratio * total_remaining / total_ratio))
            append(value - distributed)
            total_remaining -= distributed
            total_ratio -= ratio
        else:
            append(value)
    return result
''',
    mutation=(
        "            distributed = max(minimum, ceil(ratio * total_remaining / total_ratio))\n",
        "            distributed = ceil(ratio * total_remaining / total_ratio)\n",
    ),
    tests='''from src import ratio_distribute, ratio_reduce


def test_minimums():
    assert ratio_distribute(10, [1, 1], minimums=[8, 1]) == [8, 2]


def test_no_minimums():
    assert ratio_distribute(10, [1, 1]) == [5, 5]
    assert ratio_distribute(10, [1, 2]) == [4, 6]


def test_sum():
    out = ratio_distribute(17, [3, 1, 2], minimums=[1, 5, 1])
    assert sum(out) == 17 and out[1] >= 5


def test_reduce():
    assert ratio_reduce(20, [1, 1], [10, 10], [15, 15]) == [5, 5]
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_chop_cells",
    source="rich/cells.py::chop_cells",
    problem_statement="""chop_cells drops the final partial chunk

```python
>>> chop_cells("abcdefgh", 3)
['abc', 'def']
```

`'gh'` is lost, so the last line of wrapped text disappears. With a string whose length is a multiple of the width it works.
""",
    gold='''from functools import lru_cache
import unicodedata


@lru_cache(4096)
def cached_cell_len(text: str) -> int:
    return _cell_len(text)


def cell_len(text: str) -> int:
    """Get the number of cells required to display text.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if len(text) < 512:
        return cached_cell_len(text)
    return _cell_len(text)


def get_character_cell_size(character: str) -> int:
    """Get the cell size of a character."""
    if unicodedata.combining(character):
        return 0
    if unicodedata.east_asian_width(character) in ("W", "F"):
        return 2
    if ord(character) < 32:
        return 0
    return 1


def _cell_len(text: str) -> int:
    return sum(get_character_cell_size(c) for c in text)


def set_cell_size(text: str, total: int) -> str:
    """Set the length of a string to fit within given number of cells."""
    cell_size = cell_len(text)
    if cell_size == total:
        return text
    if cell_size < total:
        return text + " " * (total - cell_size)
    # Truncate character by character (slow but correct for wide chars)
    out = ""
    size = 0
    for character in text:
        char_size = get_character_cell_size(character)
        if size + char_size > total:
            break
        out += character
        size += char_size
    return out + " " * (total - size)


def chop_cells(text: str, width: int) -> list:
    """Split text into lines such that each line fits within the available (cell) width.

    Args:
        text: The text to fold such that it fits in the given width.
        width: The width available (number of cells).

    Returns:
        A list of strings such that each string in the list has cell width
        less than or equal to the available width.
    """
    _cell_len = cell_len
    lines: list = [[]]

    append_new_line = lines.append
    append_to_last_line = lines[-1].append

    total_width = 0

    for character in text:
        cell_width = _cell_len(character)
        char_doesnt_fit = total_width + cell_width > width

        if char_doesnt_fit:
            append_new_line([character])
            append_to_last_line = lines[-1].append
            total_width = cell_width
        else:
            append_to_last_line(character)
            total_width += cell_width

    return ["".join(line) for line in lines]
''',
    mutation=(
        '    return ["".join(line) for line in lines]\n',
        '    return ["".join(line) for line in lines if len(line) == width]\n',
    ),
    tests='''from src import chop_cells, set_cell_size, cell_len


def test_partial_tail():
    assert chop_cells("abcdefgh", 3) == ["abc", "def", "gh"]


def test_exact_multiple():
    assert chop_cells("abcdef", 3) == ["abc", "def"]


def test_wide_chars():
    assert chop_cells("日本語", 4) == ["日本", "語"]


def test_set_cell_size():
    assert set_cell_size("ab", 4) == "ab  "
    assert set_cell_size("abcdef", 3) == "abc"
    assert cell_len("日本") == 4
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_filesize_decimal",
    source="rich/filesize.py::decimal",
    problem_statement="""filesize.decimal shows wrong unit for exact kilobytes

```python
>>> decimal(1000)
'1000 bytes'
>>> decimal(1000000)
'1000.0 kB'
```

Expected `'1.0 kB'` and `'1.0 MB'`. Values just above the boundary (1001) are formatted correctly.
""",
    gold='''"""Functions for reporting filesizes. Borrowed from https://github.com/PyFilesystem/pyfilesystem2"""

from typing import Iterable, List, Optional, Tuple


def _to_str(
    size: int,
    suffixes: Iterable[str],
    base: int,
    *,
    precision: Optional[int] = 1,
    separator: Optional[str] = " ",
) -> str:
    if size == 1:
        return "1 byte"
    elif size < base:
        return "{:,} bytes".format(size)

    for i, suffix in enumerate(suffixes, 2):  # noqa: B007
        unit = base**i
        if size < unit:
            break
    return "{:,.{precision}f}{separator}{}".format(
        (base * size / unit),
        suffix,
        precision=precision,
        separator=separator,
    )


def pick_unit_and_suffix(size: int, suffixes: List[str], base: int) -> Tuple[int, str]:
    """Pick a suffix and base for the given size."""
    for i, suffix in enumerate(suffixes):
        unit = base**i
        if size < unit * base:
            break
    return unit, suffix


def decimal(
    size: int,
    *,
    precision: Optional[int] = 1,
    separator: Optional[str] = " ",
) -> str:
    """Convert a filesize in to a string (powers of 1000, SI prefixes).

    In this convention, ``1000 B = 1 kB``.

    Arguments:
        int (size): A file size.
        int (precision): The number of decimal places to include (default=1).
        str (separator): The string to separate the value from the units (default=" ").

    Returns:
        `str`: A string containing a abbreviated file size and units.

    Example:
        >>> filesize.decimal(30000)
        '30.0 kB'
        >>> filesize.decimal(30000, precision=2, separator="")
        '30.00kB'

    """
    return _to_str(
        size,
        ("kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"),
        1000,
        precision=precision,
        separator=separator,
    )
''',
    mutation=(
        '    elif size < base:\n        return "{:,} bytes".format(size)\n',
        '    elif size <= base:\n        return "{:,} bytes".format(size)\n',
    ),
    tests='''from src import decimal, pick_unit_and_suffix


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
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_divide_line",
    source="rich/_wrap.py::divide_line",
    problem_statement="""Word wrapping breaks one character too early

```python
>>> divide_line("foo bar baz", 7)
[4]
```

"foo bar" is exactly 7 cells and should fit on the first line, so the expected result is `[8]` (break before "baz"). It looks like a word that exactly fills the width is pushed to the next line.
""",
    gold='''import re
from typing import Iterable, List, Tuple

re_word = re.compile(r"\\s*\\S+\\s*")


def cell_len(text: str) -> int:
    return len(text)


def chop_cells(text: str, width: int) -> List[str]:
    return [text[i : i + width] for i in range(0, len(text), width)] or [""]


def loop_last(values):
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value


def words(text: str) -> Iterable[Tuple[int, int, str]]:
    """Yields each word from the text as a tuple
    containing (start_index, end_index, word). A "word" in this context may
    include the actual word and any whitespace to the right.
    """
    position = 0
    word_match = re_word.match(text, position)
    while word_match is not None:
        start, end = word_match.span()
        word = word_match.group(0)
        yield start, end, word
        word_match = re_word.match(text, end)


def divide_line(text: str, width: int, fold: bool = True) -> List[int]:
    """Given a string of text, and a width (measured in cells), return a list
    of cell offsets which the string should be split at in order for it to fit
    within the given width.

    Args:
        text: The text to examine.
        width: The available cell width.
        fold: If True, words longer than `width` will be folded onto a new line.

    Returns:
        A list of indices to break the line at.
    """
    break_positions: List[int] = []  # offsets to insert the breaks at
    append = break_positions.append
    cell_offset = 0
    _cell_len = cell_len

    for start, _end, word in words(text):
        word_length = _cell_len(word.rstrip())
        remaining_space = width - cell_offset
        word_fits_remaining_space = remaining_space >= word_length

        if word_fits_remaining_space:
            # Simplest case - the word fits within the remaining width for this line.
            cell_offset += _cell_len(word)
        else:
            # Not enough space remaining for this word on the current line.
            if word_length > width:
                # The word doesn't fit on any line, so we can't simply
                # place it on the next line...
                if fold:
                    # Fold the word across multiple lines.
                    folded_word = chop_cells(word, width=width)
                    for last, line in loop_last(folded_word):
                        if start:
                            append(start)
                        if last:
                            cell_offset = _cell_len(line)
                        else:
                            start += len(line)
                else:
                    # Folding isn't allowed, so crop the word.
                    if start:
                        append(start)
                    cell_offset = _cell_len(word)
            elif cell_offset and start:
                # The word doesn't fit within the remaining space on the current
                # line, but it *can* fit on to the next (empty) line.
                append(start)
                cell_offset = _cell_len(word)

    return break_positions
''',
    mutation=(
        "        word_fits_remaining_space = remaining_space >= word_length\n",
        "        word_fits_remaining_space = remaining_space > word_length\n",
    ),
    tests='''from src import divide_line, words


def test_exact_fit():
    assert divide_line("foo bar baz", 7) == [8]


def test_basic():
    assert divide_line("foo bar baz", 5) == [4, 8]


def test_no_break():
    assert divide_line("foo bar", 20) == []


def test_fold_long():
    assert divide_line("abcdefghij", 4) == [4, 8]


def test_words():
    assert [w for _, _, w in words("a  bb c")] == ["a  ", "bb ", "c"]
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_color_triplet",
    source="rich/color_triplet.py::ColorTriplet",
    problem_statement="""ColorTriplet.hex produces 5-digit colours for small components

```python
>>> ColorTriplet(0, 128, 255).hex
'#080ff'
```

Expected `'#0080ff'`. Components below 16 are not zero-padded. `rgb` and `normalized` are fine.
""",
    gold='''from typing import NamedTuple, Tuple


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
        return f"#{red:02x}{green:02x}{blue:02x}"

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
''',
    mutation=(
        '        return f"#{red:02x}{green:02x}{blue:02x}"\n',
        '        return f"#{red:x}{green:x}{blue:x}"\n',
    ),
    tests='''from src import ColorTriplet, parse_rgb_hex, blend_rgb


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
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_markup_escape",
    source="rich/markup.py::escape",
    problem_statement="""markup.escape does not escape closing tags

```python
>>> escape("[/bold]")
'[/bold]'
```

Rendering the escaped string still closes the current style. Opening tags like `[bold]` are escaped to `\\[bold]` as expected, so only the `[/...]` form is affected.
""",
    gold='''import re
from typing import Match

RE_TAGS = re.compile(
    r"""((\\\\*)\\[([a-z#/@][^[]*?)])""",
    re.VERBOSE,
)


def escape(
    markup: str,
    _escape=re.compile(r"(\\\\*)(\\[[a-z#/@][^[]*?])").sub,
) -> str:
    """Escapes text so that it won't be interpreted as markup.

    Args:
        markup (str): Content to be inserted in to markup.

    Returns:
        str: Markup with square brackets escaped.
    """

    def escape_backslashes(match: Match[str]) -> str:
        """Called by re.sub replace matches."""
        backslashes, text = match.groups()
        return f"{backslashes}{backslashes}\\\\{text}"

    markup = _escape(escape_backslashes, markup)
    if markup.endswith("\\\\") and not markup.endswith("\\\\\\\\"):
        return markup + "\\\\"

    return markup


def strip_tags(markup: str) -> str:
    """Remove (non-escaped) tags from a markup string."""
    out = []
    position = 0
    for match in RE_TAGS.finditer(markup):
        full_text, escapes, tag_text = match.groups()
        start, end = match.span()
        out.append(markup[position:start])
        if escapes:
            out.append(full_text[len(escapes) :])
        position = end
    out.append(markup[position:])
    return "".join(out)
''',
    mutation=(
        '    _escape=re.compile(r"(\\\\*)(\\[[a-z#/@][^[]*?])").sub,\n',
        '    _escape=re.compile(r"(\\\\*)(\\[[a-z#@][^[]*?])").sub,\n',
    ),
    tests='''from src import escape, strip_tags


def test_escape_closing():
    assert escape("[/bold]") == "\\\\[/bold]"


def test_escape_opening():
    assert escape("[bold]x") == "\\\\[bold]x"


def test_plain_untouched():
    assert escape("[1, 2]") == "[1, 2]"
    assert escape("hello") == "hello"


def test_strip_tags():
    assert strip_tags("[bold]hi[/bold]") == "hi"
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_lookup_pick_bool",
    source="rich/_pick.py::pick_bool",
    problem_statement="""pick_bool returns None when the first value is False

```python
>>> pick_bool(False, True)
True
```

Expected `False`: the first value that is not `None` must win. With `pick_bool(None, True)` the result is correctly `True`, so only explicit `False` is skipped.
""",
    gold='''from typing import Optional


def pick_bool(*values: Optional[bool]) -> bool:
    """Pick the first non-none bool or return the last value.

    Args:
        *values (bool): Any number of boolean or None values.

    Returns:
        bool: First non-none boolean.
    """
    assert values, "1 or more values required"
    for value in values:
        if value is not None:
            return value
    return bool(value)


def pick_first_str(*values: Optional[str]) -> Optional[str]:
    """Pick the first string that is not None."""
    for value in values:
        if value is not None:
            return value
    return None
''',
    mutation=(
        "    for value in values:\n        if value is not None:\n            return value\n    return bool(value)\n",
        "    for value in values:\n        if value:\n            return value\n    return bool(value)\n",
    ),
    tests='''from src import pick_bool, pick_first_str


def test_false_first():
    assert pick_bool(False, True) is False


def test_none_skipped():
    assert pick_bool(None, True) is True
    assert pick_bool(None, None, False) is False


def test_all_none():
    assert pick_bool(None, None) is False


def test_pick_str():
    assert pick_first_str(None, "", "x") == ""
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_ansi_strip",
    source="rich/ansi.py (simplified)::strip_ansi",
    problem_statement="""strip_ansi leaves OSC hyperlink sequences in the output

```python
>>> strip_ansi("\\x1b]8;;http://x\\x1b\\\\link\\x1b]8;;\\x1b\\\\")
'\\x1b]8;;http://x\\x1b\\\\link\\x1b]8;;\\x1b\\\\'
```

Expected `'link'`. Colour codes such as `\\x1b[31m` are stripped correctly.
""",
    gold='''import re

# CSI sequences: ESC [ ... final byte
_CSI = r"\\x1b\\[[0-?]*[ -/]*[@-~]"
# OSC sequences: ESC ] ... terminated by BEL or ESC \\\\
_OSC = r"\\x1b\\][^\\x07\\x1b]*(?:\\x07|\\x1b\\\\)"

re_ansi = re.compile(f"(?:{_CSI})|(?:{_OSC})")


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences (CSI and OSC) from text."""
    return re_ansi.sub("", text)


def ansi_len(text: str) -> int:
    """Visible length of text once escape codes are removed."""
    return len(strip_ansi(text))
''',
    mutation=(
        're_ansi = re.compile(f"(?:{_CSI})|(?:{_OSC})")\n',
        're_ansi = re.compile(f"(?:{_CSI})")\n',
    ),
    tests='''from src import strip_ansi, ansi_len


def test_osc_hyperlink():
    assert strip_ansi("\\x1b]8;;http://x\\x1b\\\\link\\x1b]8;;\\x1b\\\\") == "link"


def test_csi_colour():
    assert strip_ansi("\\x1b[31mred\\x1b[0m") == "red"


def test_plain():
    assert strip_ansi("plain") == "plain"
    assert ansi_len("\\x1b[1mab\\x1b[0m") == 2


def test_osc_bel():
    assert strip_ansi("\\x1b]0;title\\x07text") == "text"
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_ratio_resolve",
    source="rich/_ratio.py::ratio_resolve",
    problem_statement="""Layout with a fixed-size and a flexible region overflows

Given a total of 10 and two edges, one with `size=3` and one flexible with `ratio=1`, `ratio_resolve` returns `[3, 10]` — the flexible region gets the whole total instead of the remaining 7, so the layout is 3 rows too tall.
""",
    gold='''from fractions import Fraction
from math import ceil
from typing import List, Optional, Sequence


class Edge:
    """Any object that defines an edge (such as Layout)."""

    size: Optional[int] = None
    ratio: int = 1
    minimum_size: int = 1

    def __init__(self, size=None, ratio=1, minimum_size=1):
        self.size = size
        self.ratio = ratio
        self.minimum_size = minimum_size


def ratio_resolve(total: int, edges: Sequence[Edge]) -> List[int]:
    """Divide total space to satisfy size, ratio, and minimum_size, constraints.

    The returned list of integers should add up to total in most cases, unless it is
    impossible to satisfy all the constraints. For instance, if there are two edges
    with a minimum size of 20 each and `total` is 30 then the returned list will be
    greater than total. In practice, this would mean that a Layout object would
    clip the rows that would overflow the screen height.

    Args:
        total (int): Total number of characters.
        edges (List[Edge]): Edges within total space.

    Returns:
        List[int]: Number of characters for each edge.
    """
    # Size of edge or None for yet to be determined
    sizes = [(edge.size or None) for edge in edges]

    _Fraction = Fraction

    # While any edges haven't been calculated
    while None in sizes:
        # Get flexible edges and index to map these back on to sizes list
        flexible_edges = [
            (index, edge)
            for index, (size, edge) in enumerate(zip(sizes, edges))
            if size is None
        ]
        # Remaining space in total
        remaining = total - sum(size or 0 for size in sizes)
        if remaining <= 0:
            # No room for flexible edges
            return [
                ((edge.minimum_size or 1) if size is None else size)
                for size, edge in zip(sizes, edges)
            ]
        # Calculate number of characters in a ratio portion
        portion = _Fraction(
            remaining, sum((edge.ratio or 1) for _, edge in flexible_edges)
        )

        # If any edges will be less than their minimum, replace size with the minimum
        for index, edge in flexible_edges:
            if portion * edge.ratio <= edge.minimum_size:
                sizes[index] = edge.minimum_size
                # New fixed size will invalidate calculations, so we need to repeat the process
                break
        else:
            # Distribute flexible space and compensate for rounding error
            # Since edge sizes can only be integers we need to add the remainder
            # to the following line
            remainder = _Fraction(0)
            for index, edge in flexible_edges:
                size, remainder = divmod(portion * edge.ratio + remainder, 1)
                sizes[index] = int(size)
            break
    # Sizes now contains integers only
    return sizes  # type: ignore[return-value]
''',
    mutation=(
        "        remaining = total - sum(size or 0 for size in sizes)\n",
        "        remaining = total\n",
    ),
    tests='''from src import ratio_resolve, Edge


def test_fixed_plus_flexible():
    assert ratio_resolve(10, [Edge(size=3), Edge(ratio=1)]) == [3, 7]


def test_two_flexible():
    assert ratio_resolve(10, [Edge(ratio=1), Edge(ratio=1)]) == [5, 5]


def test_minimum():
    assert ratio_resolve(10, [Edge(size=8), Edge(ratio=1, minimum_size=3)]) == [8, 3]


def test_rounding():
    assert sum(ratio_resolve(10, [Edge(ratio=1), Edge(ratio=1), Edge(ratio=1)])) == 10
''',
)

# ---------------------------------------------------------------------------
task(
    id="rich_style_parse_color",
    source="rich/color.py (simplified)::parse_color",
    problem_statement="""Hex colours with uppercase digits are rejected

```python
>>> parse_color("#FF8800")
ColorParseError: '#FF8800' is not a valid color
```

Lowercase `#ff8800` works. CSS hex colours are case-insensitive, so uppercase should be accepted too.
""",
    gold='''import re
from typing import NamedTuple, Optional, Tuple


class ColorParseError(Exception):
    """The color could not be parsed."""


class ColorTriplet(NamedTuple):
    red: int
    green: int
    blue: int


RE_COLOR = re.compile(
    r"""^
\\#([0-9a-f]{6})$|
color\\(([0-9]{1,3})\\)$|
rgb\\(([\\d\\s,]+)\\)$
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
    color = color.lower().strip()

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
''',
    mutation=(
        "    original_color = color\n    color = color.lower().strip()\n",
        "    original_color = color\n    color = color.strip()\n",
    ),
    tests='''import pytest
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
''',
)
