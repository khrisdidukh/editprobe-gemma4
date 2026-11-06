from src import TextChunker, TextDecoder


def test_chunks():
    c = TextChunker(chunk_size=2)
    assert c.decode("abcde") == ["ab", "cd"]
    assert c.flush() == ["e"]


def test_exact():
    c = TextChunker(chunk_size=3)
    assert c.decode("abcdef") == ["abc", "def"]
    assert c.flush() == []


def test_none():
    c = TextChunker()
    assert c.decode("abc") == ["abc"]


def test_decoder():
    d = TextDecoder()
    assert d.decode("é".encode()[:1]) == ""
    assert d.decode("é".encode()[1:]) == "é"
