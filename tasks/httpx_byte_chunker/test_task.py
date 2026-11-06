from src import ByteChunker


def test_remainder_carried():
    c = ByteChunker(chunk_size=3)
    assert c.decode(b"abcdefgh") == [b"abc", b"def"]
    assert c.decode(b"ij") == [b"ghi"]
    assert c.flush() == [b"j"]


def test_exact():
    c = ByteChunker(chunk_size=2)
    assert c.decode(b"abcd") == [b"ab", b"cd"]
    assert c.flush() == []


def test_none_chunk_size():
    c = ByteChunker()
    assert c.decode(b"abc") == [b"abc"]
    assert c.decode(b"") == []


def test_small_pieces():
    c = ByteChunker(chunk_size=4)
    assert c.decode(b"a") == []
    assert c.decode(b"b") == []
    assert c.decode(b"cd") == [b"abcd"]
