from functools import lru_cache
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
