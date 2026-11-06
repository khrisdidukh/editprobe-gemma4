import re
from typing import Iterable, List, Tuple

re_word = re.compile(r"\s*\S+\s*")


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
        word_fits_remaining_space = remaining_space > word_length

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
