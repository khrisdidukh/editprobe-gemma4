from src import LineDecoder


def test_no_trailing_newline():
    d = LineDecoder()
    assert d.decode("a\nb\nc") == ["a", "b"]
    assert d.flush() == ["c"]


def test_trailing_newline():
    d = LineDecoder()
    assert d.decode("a\nb\n") == ["a", "b"]
    assert d.flush() == []


def test_split_across_chunks():
    d = LineDecoder()
    assert d.decode("ab") == []
    assert d.decode("c\nd") == ["abc"]
    assert d.flush() == ["d"]


def test_crlf_across_chunks():
    d = LineDecoder()
    assert d.decode("a\r") == []
    assert d.decode("\nb\r\n") == ["a", "b"]
    assert d.flush() == []
