from src import strip_ansi, ansi_len


def test_osc_hyperlink():
    assert strip_ansi("\x1b]8;;http://x\x1b\\link\x1b]8;;\x1b\\") == "link"


def test_csi_colour():
    assert strip_ansi("\x1b[31mred\x1b[0m") == "red"


def test_plain():
    assert strip_ansi("plain") == "plain"
    assert ansi_len("\x1b[1mab\x1b[0m") == 2


def test_osc_bel():
    assert strip_ansi("\x1b]0;title\x07text") == "text"
