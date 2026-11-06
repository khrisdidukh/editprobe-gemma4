import io
from src import peek_filelike_length, to_bytes


def test_partially_read():
    f = io.BytesIO(b"0123456789")
    f.read(3)
    assert peek_filelike_length(f) == 7
    assert f.tell() == 3


def test_fresh():
    assert peek_filelike_length(io.BytesIO(b"abcd")) == 4


def test_not_seekable():
    class S:
        pass

    assert peek_filelike_length(S()) is None


def test_to_bytes():
    assert to_bytes("é") == "é".encode()
    assert to_bytes(b"x") == b"x"
