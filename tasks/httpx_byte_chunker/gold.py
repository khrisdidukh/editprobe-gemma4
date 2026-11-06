import io
from typing import List, Optional


class ByteChunker:
    """
    Handles returning byte content in fixed-size chunks.
    """

    def __init__(self, chunk_size: Optional[int] = None) -> None:
        self._buffer = io.BytesIO()
        self._chunk_size = chunk_size

    def decode(self, content: bytes) -> List[bytes]:
        if self._chunk_size is None:
            return [content] if content else []

        self._buffer.write(content)
        if self._buffer.tell() >= self._chunk_size:
            value = self._buffer.getvalue()
            chunks = [
                value[i : i + self._chunk_size]
                for i in range(0, len(value), self._chunk_size)
            ]
            if len(chunks[-1]) == self._chunk_size:
                self._buffer.seek(0)
                self._buffer.truncate()
                return chunks
            else:
                self._buffer.seek(0)
                self._buffer.write(chunks[-1])
                self._buffer.truncate()
                return chunks[:-1]
        else:
            return []

    def flush(self) -> List[bytes]:
        value = self._buffer.getvalue()
        self._buffer.seek(0)
        self._buffer.truncate()
        return [value] if value else []
