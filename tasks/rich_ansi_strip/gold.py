import re

# CSI sequences: ESC [ ... final byte
_CSI = r"\x1b\[[0-?]*[ -/]*[@-~]"
# OSC sequences: ESC ] ... terminated by BEL or ESC \\
_OSC = r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"

re_ansi = re.compile(f"(?:{_CSI})|(?:{_OSC})")


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences (CSI and OSC) from text."""
    return re_ansi.sub("", text)


def ansi_len(text: str) -> int:
    """Visible length of text once escape codes are removed."""
    return len(strip_ansi(text))
