import io
from src import super_len


def test_partially_read():
    f = io.BytesIO(b"0123456789")
    f.read(4)
    assert super_len(f) == 6


def test_str_and_bytes():
    assert super_len("héllo") == 6
    assert super_len(b"abc") == 3


def test_bytesio_full():
    assert super_len(io.BytesIO(b"abcd")) == 4


def test_restores_position():
    f = io.BytesIO(b"0123456789")
    f.read(2)
    super_len(f)
    assert f.tell() == 2
