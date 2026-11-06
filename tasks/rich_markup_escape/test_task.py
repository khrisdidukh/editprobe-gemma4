from src import escape, strip_tags


def test_escape_closing():
    assert escape("[/bold]") == "\\[/bold]"


def test_escape_opening():
    assert escape("[bold]x") == "\\[bold]x"


def test_plain_untouched():
    assert escape("[1, 2]") == "[1, 2]"
    assert escape("hello") == "hello"


def test_strip_tags():
    assert strip_tags("[bold]hi[/bold]") == "hi"
