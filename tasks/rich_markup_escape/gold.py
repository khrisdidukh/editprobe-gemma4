import re
from typing import Match

RE_TAGS = re.compile(
    r"""((\\*)\[([a-z#/@][^[]*?)])""",
    re.VERBOSE,
)


def escape(
    markup: str,
    _escape=re.compile(r"(\\*)(\[[a-z#/@][^[]*?])").sub,
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
        return f"{backslashes}{backslashes}\\{text}"

    markup = _escape(escape_backslashes, markup)
    if markup.endswith("\\") and not markup.endswith("\\\\"):
        return markup + "\\"

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
