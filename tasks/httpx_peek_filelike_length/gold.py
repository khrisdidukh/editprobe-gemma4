import os
import typing


def peek_filelike_length(stream: typing.Any) -> typing.Optional[int]:
    """
    Given a file-like stream object, return its length in number of bytes
    without reading it into memory.
    """
    try:
        # Is it an actual file?
        fd = stream.fileno()
        # Yup, seems to be an actual file.
        length = os.fstat(fd).st_size
    except (AttributeError, OSError):
        # No... Maybe it's something that supports random access, like `io.BytesIO`?
        try:
            # Assuming so, go to end of stream to figure out its length,
            # then put it back in place.
            offset = stream.tell()
            length = stream.seek(0, os.SEEK_END)
            stream.seek(offset)
        except (AttributeError, OSError):
            # Not even that? Sorry, we're doomed...
            return None

    try:
        offset = stream.tell()
    except (AttributeError, OSError):
        return length
    return length - offset


def to_bytes(value: typing.Union[str, bytes], encoding: str = "utf-8") -> bytes:
    return value.encode(encoding) if isinstance(value, str) else value
