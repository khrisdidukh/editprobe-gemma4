"""Tasks adapted from encode/httpx (BSD-3-Clause). Standalone modules; see tasks_requests.py."""

TASKS = []


def task(**kw):
    TASKS.append(kw)


# ---------------------------------------------------------------------------
task(
    id="httpx_line_decoder",
    source="httpx/_decoders.py::LineDecoder",
    problem_statement="""iter_lines() loses the last line when the body has no trailing newline

```python
>>> d = LineDecoder()
>>> d.decode("a\\nb\\nc")
['a', 'b']
>>> d.flush()
[]
```

The final `"c"` never comes out. If the body ends with `\\n` everything is fine.
""",
    gold='''from typing import List


class LineDecoder:
    """
    Handles incrementally reading lines from text.

    Has the same behaviour as the stdllib splitlines,
    but handling the input iteratively.
    """

    def __init__(self) -> None:
        self.buffer: List[str] = []
        self.trailing_cr: bool = False

    def decode(self, text: str) -> List[str]:
        # See https://docs.python.org/3/library/stdtypes.html#str.splitlines
        NEWLINE_CHARS = "\\n\\r\\x0b\\x0c\\x1c\\x1d\\x1e\\x85\\u2028\\u2029"

        # We always push a trailing `\\r` into the next decode iteration.
        if self.trailing_cr:
            text = "\\r" + text
            self.trailing_cr = False
        if text.endswith("\\r"):
            self.trailing_cr = True
            text = text[:-1]

        if not text:
            # NOTE: the edge case input of empty text doesn't occur in practice,
            # because other httpx internals filter out this value
            return []  # pragma: no cover

        trailing_newline = text[-1] in NEWLINE_CHARS
        lines = text.splitlines()

        if len(lines) == 1 and not trailing_newline:
            # No new lines, buffer the input and continue.
            self.buffer.append(lines[0])
            return []

        if self.buffer:
            # Include any existing buffer in the first portion of the
            # splitlines result.
            lines = ["".join(self.buffer) + lines[0]] + lines[1:]
            self.buffer = []

        if not trailing_newline:
            # If the last segment of splitlines is not newline terminated,
            # then drop it from our output and start a new buffer.
            self.buffer = [lines.pop()]

        return lines

    def flush(self) -> List[str]:
        if not self.buffer and not self.trailing_cr:
            return []

        lines = ["".join(self.buffer)]
        self.buffer = []
        self.trailing_cr = False
        return lines
''',
    mutation=(
        "    def flush(self) -> List[str]:\n        if not self.buffer and not self.trailing_cr:\n            return []\n",
        "    def flush(self) -> List[str]:\n        if not self.trailing_cr:\n            return []\n",
    ),
    tests='''from src import LineDecoder


def test_no_trailing_newline():
    d = LineDecoder()
    assert d.decode("a\\nb\\nc") == ["a", "b"]
    assert d.flush() == ["c"]


def test_trailing_newline():
    d = LineDecoder()
    assert d.decode("a\\nb\\n") == ["a", "b"]
    assert d.flush() == []


def test_split_across_chunks():
    d = LineDecoder()
    assert d.decode("ab") == []
    assert d.decode("c\\nd") == ["abc"]
    assert d.flush() == ["d"]


def test_crlf_across_chunks():
    d = LineDecoder()
    assert d.decode("a\\r") == []
    assert d.decode("\\nb\\r\\n") == ["a", "b"]
    assert d.flush() == []
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_byte_chunker",
    source="httpx/_decoders.py::ByteChunker",
    problem_statement="""ByteChunker emits chunks larger than chunk_size

```python
>>> c = ByteChunker(chunk_size=3)
>>> c.decode(b"abcdefgh")
[b'abc', b'def']
>>> c.decode(b"ij")
[b'ghij']
```

The second call returned a 4-byte chunk although `chunk_size=3`. Expected `[b'ghi']` and then `b'j'` on flush.
""",
    gold='''import io
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
''',
    mutation=(
        "                self._buffer.seek(0)\n                self._buffer.write(chunks[-1])\n                self._buffer.truncate()\n                return chunks[:-1]\n",
        "                self._buffer.write(chunks[-1])\n                self._buffer.truncate()\n                return chunks[:-1]\n",
    ),
    tests='''from src import ByteChunker


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
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_normalize_port",
    source="httpx/_urlparse.py::normalize_port",
    problem_statement="""Default port not removed for https URLs

`normalize_port("443", "https")` returns `443` but should return `None`, since 443 is the default for https. For http the default port 80 is removed correctly. The result is that `https://example.com:443/` and `https://example.com/` compare as different URLs.
""",
    gold='''from typing import Optional, Union


class InvalidURL(Exception):
    pass


DEFAULT_PORTS = {
    "ftp": 21,
    "http": 80,
    "https": 443,
    "ws": 80,
    "wss": 443,
}


def normalize_port(port: Union[str, int, None], scheme: str) -> Optional[int]:
    # From https://tools.ietf.org/html/rfc3986#section-3.2.3
    #
    # "A scheme may define a default port.  For example, the "http" scheme
    # defines a default port of "80", corresponding to its reserved TCP
    # port number.  The type of port designated by the port number can be
    # defined by the scheme.  URI producers and normalizers should omit
    # the port component and its ":" delimiter if port is empty or if its
    # value would be the same as that of the scheme's default."
    if port is None or port == "":
        return None

    try:
        port_as_int = int(port)
    except ValueError:
        raise InvalidURL(f"Invalid port: {port!r}")

    # See https://url.spec.whatwg.org/#url-miscellaneous
    default_port = DEFAULT_PORTS.get(scheme)
    if port_as_int == default_port:
        return None
    return port_as_int


def port_or_default(scheme: str, port: Optional[int]) -> Optional[int]:
    if port is not None:
        return port
    return DEFAULT_PORTS.get(scheme)
''',
    mutation=(
        '    "http": 80,\n    "https": 443,\n    "ws": 80,\n',
        '    "http": 80,\n    "https": 433,\n    "ws": 80,\n',
    ),
    tests='''import pytest
from src import normalize_port, port_or_default, InvalidURL


def test_https_default_removed():
    assert normalize_port("443", "https") is None
    assert normalize_port(443, "wss") is None


def test_http_default_removed():
    assert normalize_port("80", "http") is None


def test_non_default_kept():
    assert normalize_port("8443", "https") == 8443
    assert normalize_port("", "https") is None


def test_invalid():
    with pytest.raises(InvalidURL):
        normalize_port("abc", "http")


def test_port_or_default():
    assert port_or_default("https", None) == 443
    assert port_or_default("http", 8080) == 8080
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_obfuscate_headers",
    source="httpx/_utils.py::obfuscate_sensitive_headers",
    problem_statement="""Proxy-Authorization is printed in clear text

When logging request headers, `Authorization` is replaced with `[secure]`, but `Proxy-Authorization` is shown as-is, leaking proxy credentials in logs.
""",
    gold='''from typing import Iterable, Iterator, Tuple, Union

SENSITIVE_HEADERS = {"authorization", "proxy-authorization"}


def to_str(value: Union[str, bytes], encoding: str = "utf-8") -> str:
    return value if isinstance(value, str) else value.decode(encoding)


def obfuscate_sensitive_headers(
    items: Iterable[Tuple[Union[str, bytes], Union[str, bytes]]],
) -> Iterator[Tuple[Union[str, bytes], Union[str, bytes]]]:
    for k, v in items:
        if to_str(k.lower()) in SENSITIVE_HEADERS:
            v = to_bytes_or_str("[secure]", match_type_of=v)
        yield k, v


def to_bytes_or_str(value: str, match_type_of):
    return value if isinstance(match_type_of, str) else value.encode()


def format_headers(items: Iterable[Tuple[str, str]]) -> str:
    """Render headers for logging, one per line."""
    return "\\n".join(f"{k}: {v}" for k, v in obfuscate_sensitive_headers(items))
''',
    mutation=(
        'SENSITIVE_HEADERS = {"authorization", "proxy-authorization"}\n',
        'SENSITIVE_HEADERS = {"authorization"}\n',
    ),
    tests='''from src import obfuscate_sensitive_headers, format_headers


def test_proxy_auth_hidden():
    out = dict(obfuscate_sensitive_headers([("Proxy-Authorization", "Basic abc")]))
    assert out == {"Proxy-Authorization": "[secure]"}


def test_auth_hidden():
    out = dict(obfuscate_sensitive_headers([("Authorization", "Bearer x")]))
    assert out == {"Authorization": "[secure]"}


def test_bytes():
    out = dict(obfuscate_sensitive_headers([(b"authorization", b"x")]))
    assert out == {b"authorization": b"[secure]"}


def test_others_untouched():
    assert format_headers([("Host", "example.com"), ("Authorization", "x")]) == "Host: example.com\\nAuthorization: [secure]"
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_same_origin",
    source="httpx/_client.py (simplified)::same_origin, is_https_redirect",
    problem_statement="""Authorization header is dropped on http -> https redirect to the same host

Redirecting `http://example.com/` to `https://example.com/` should keep the Authorization header (this is the one cross-scheme case that is allowed), but it is being stripped. Redirects to a different host correctly strip it.
""",
    gold='''from typing import NamedTuple, Optional

DEFAULT_PORTS = {"http": 80, "https": 443}


class URL(NamedTuple):
    scheme: str
    host: str
    port: Optional[int] = None


def port_or_default(url: URL) -> Optional[int]:
    if url.port is not None:
        return url.port
    return DEFAULT_PORTS.get(url.scheme)


def same_origin(url: URL, other: URL) -> bool:
    """
    Return 'True' if the given URLs share the same origin.
    """
    return (
        url.scheme == other.scheme
        and url.host == other.host
        and port_or_default(url) == port_or_default(other)
    )


def is_https_redirect(url: URL, location: URL) -> bool:
    """
    Return 'True' if 'location' is a HTTPS upgrade of 'url'
    """
    if url.host != location.host:
        return False

    return (
        url.scheme == "http"
        and port_or_default(url) == 80
        and location.scheme == "https"
        and port_or_default(location) == 443
    )


def redirect_headers(headers: dict, url: URL, location: URL) -> dict:
    """Return the headers to send on a redirect."""
    headers = dict(headers)
    if not same_origin(url, location):
        if not is_https_redirect(url, location):
            # Strip Authorization headers when responses are redirected
            # away from the origin. (Except for direct HTTP to HTTPS redirects.)
            headers.pop("Authorization", None)
    return headers
''',
    mutation=(
        "        and location.scheme == \"https\"\n        and port_or_default(location) == 443\n",
        "        and location.scheme == \"https\"\n        and location.port == 443\n",
    ),
    tests='''from src import URL, same_origin, is_https_redirect, redirect_headers


def test_https_upgrade_keeps_auth():
    h = {"Authorization": "x", "Accept": "*/*"}
    assert redirect_headers(h, URL("http", "example.com"), URL("https", "example.com")) == h


def test_explicit_443():
    assert is_https_redirect(URL("http", "example.com"), URL("https", "example.com", 443))


def test_other_host_strips():
    h = {"Authorization": "x"}
    assert redirect_headers(h, URL("http", "a.com"), URL("http", "b.com")) == {}


def test_same_origin():
    assert same_origin(URL("https", "a.com"), URL("https", "a.com", 443))
    assert not same_origin(URL("http", "a.com"), URL("https", "a.com"))
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_url_pattern",
    source="httpx/_utils.py::URLPattern",
    problem_statement="""Proxy pattern "http://" matches https URLs

A proxy configured only for `"http://"` is also used for `https://example.com`. The pattern should match only the http scheme. Patterns with host and port behave correctly.
""",
    gold='''import re
from typing import NamedTuple, Optional


class URL(NamedTuple):
    scheme: str
    host: str
    port: Optional[int] = None


class URLPattern:
    """
    A utility class currently used for making lookups against proxy keys...

    # Wildcard matching...
    >>> pattern = URLPattern("all://")
    >>> pattern.matches(URL("http://example.com"))
    True

    # Witch scheme matching...
    >>> pattern = URLPattern("https://")
    >>> pattern.matches(URL("https://example.com"))
    True
    >>> pattern.matches(URL("http://example.com"))
    False
    """

    def __init__(self, pattern: str) -> None:
        if pattern and ":" not in pattern:
            raise ValueError(
                f"Proxy keys should use proper URL forms rather "
                f"than plain scheme strings. "
                f'Instead of "{pattern}", use "{pattern}://"'
            )

        scheme, _, rest = pattern.partition("://")
        host = rest.split("/", 1)[0]
        port = None
        if host and ":" in host:
            host, port_str = host.rsplit(":", 1)
            port = int(port_str)

        self.pattern = pattern
        self.scheme = "" if scheme == "all" else scheme
        self.host = "" if host == "*" else host
        self.port = port
        if not host or host.startswith("*"):
            # Any domain, or any domain matching a given suffix.
            self.host_regex: Optional[re.Pattern] = None
            if host and host.startswith("*"):
                domain = re.escape(host[2:])
                self.host_regex = re.compile(f"^.+\\\\.{domain}$")
        else:
            # An exact hostname.
            self.host_regex = re.compile(f"^{re.escape(host)}$")

    def matches(self, other: URL) -> bool:
        if self.scheme and self.scheme != other.scheme:
            return False
        if (
            self.host
            and self.host_regex is not None
            and not self.host_regex.match(other.host)
        ):
            return False
        if self.port is not None and self.port != other.port:
            return False
        return True

    @property
    def priority(self):
        """
        The priority allows URLPattern instances to be sortable, so that
        we can match from most specific to least specific.
        """
        port_priority = 0 if self.port is not None else 1
        host_priority = 0 if self.host else 1
        scheme_priority = 0 if self.scheme else 1
        return (port_priority, host_priority, scheme_priority)

    def __lt__(self, other: "URLPattern") -> bool:
        return self.priority < other.priority

    def __eq__(self, other) -> bool:
        return isinstance(other, URLPattern) and self.pattern == other.pattern
''',
    mutation=(
        '        self.scheme = "" if scheme == "all" else scheme\n',
        '        self.scheme = "" if scheme in ("all", "http") else scheme\n',
    ),
    tests='''from src import URLPattern, URL


def test_http_pattern_not_https():
    p = URLPattern("http://")
    assert p.matches(URL("http", "example.com"))
    assert not p.matches(URL("https", "example.com"))


def test_all():
    assert URLPattern("all://").matches(URL("https", "x.com"))


def test_host_port():
    p = URLPattern("https://example.com:8443")
    assert p.matches(URL("https", "example.com", 8443))
    assert not p.matches(URL("https", "example.com", 443))


def test_wildcard_and_priority():
    assert URLPattern("all://*.example.com").matches(URL("http", "a.example.com"))
    assert not URLPattern("all://*.example.com").matches(URL("http", "example.com"))
    assert URLPattern("http://example.com") < URLPattern("http://")
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_primitive_value",
    source="httpx/_utils.py::primitive_value_to_str",
    problem_statement="""Boolean query params are sent as "True"/"False"

```python
>>> primitive_value_to_str(True)
'True'
```

Expected `'true'` (lowercase, as before). `None` correctly becomes `''`.
""",
    gold='''from typing import Optional, Union

PrimitiveData = Optional[Union[str, int, float, bool]]


def primitive_value_to_str(value: PrimitiveData) -> str:
    """
    Coerce a primitive data type into a string value.

    Note that we prefer JSON-style 'true'/'false' for boolean values here.
    """
    if value is True:
        return "true"
    elif value is False:
        return "false"
    elif value is None:
        return ""
    return str(value)


def encode_query_params(params: dict) -> str:
    """Encode a dict of primitive values as a query string (no escaping)."""
    return "&".join(f"{k}={primitive_value_to_str(v)}" for k, v in params.items())
''',
    mutation=(
        '    if value is True:\n        return "true"\n    elif value is False:\n        return "false"\n    elif value is None:\n',
        '    if value is None:\n',
    ),
    tests='''from src import primitive_value_to_str, encode_query_params


def test_bools():
    assert primitive_value_to_str(True) == "true"
    assert primitive_value_to_str(False) == "false"


def test_none_and_numbers():
    assert primitive_value_to_str(None) == ""
    assert primitive_value_to_str(1) == "1"
    assert primitive_value_to_str(1.5) == "1.5"


def test_query():
    assert encode_query_params({"a": True, "b": None, "c": "x"}) == "a=true&b=&c=x"
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_multipart_boundary",
    source="httpx/_multipart.py::get_multipart_boundary_from_content_type",
    problem_statement="""Multipart boundary with quotes is not parsed

```python
>>> get_multipart_boundary_from_content_type(b'multipart/form-data; boundary="abc123"')
b'"abc123"'
```

The quotes are kept, so the body is encoded with a boundary that does not match the header. An unquoted boundary works.
""",
    gold='''import re
from typing import Optional


def get_multipart_boundary_from_content_type(
    content_type: Optional[bytes],
) -> Optional[bytes]:
    if not content_type or not content_type.startswith(b"multipart/form-data"):
        return None
    # parse boundary according to
    # https://www.rfc-editor.org/rfc/rfc2046#section-5.1.1
    if b";" in content_type:
        for section in content_type.split(b";"):
            if section.strip().lower().startswith(b"boundary="):
                return section.strip()[len(b"boundary=") :].strip(b'"')
    return None


def _format_form_param(name: str, value: str) -> bytes:
    """
    Encode a name/value pair within a multipart form.
    """

    def replacer(match: re.Match) -> str:
        return {"\\\\": "\\\\\\\\", '"': '\\\\"'}[match.group(0)]

    value = re.sub(r'["\\\\]', replacer, value)
    return f'{name}="{value}"'.encode()
''',
    mutation=(
        "                return section.strip()[len(b\"boundary=\") :].strip(b'\"')\n",
        "                return section.strip()[len(b\"boundary=\") :]\n",
    ),
    tests='''from src import get_multipart_boundary_from_content_type, _format_form_param


def test_quoted():
    assert get_multipart_boundary_from_content_type(b'multipart/form-data; boundary="abc123"') == b"abc123"


def test_unquoted():
    assert get_multipart_boundary_from_content_type(b"multipart/form-data; boundary=abc123") == b"abc123"


def test_none():
    assert get_multipart_boundary_from_content_type(b"application/json") is None
    assert get_multipart_boundary_from_content_type(None) is None
    assert get_multipart_boundary_from_content_type(b"multipart/form-data") is None


def test_form_param():
    assert _format_form_param("name", 'a"b') == b'name="a\\\\"b"'
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_peek_filelike_length",
    source="httpx/_utils.py::peek_filelike_length",
    problem_statement="""Content-Length wrong for a file opened and partly read

```python
>>> f = io.BytesIO(b"0123456789")
>>> f.read(3)
>>> peek_filelike_length(f)
10
```

Expected 7 (the bytes that will actually be sent). The function should also leave the position unchanged, which it does.
""",
    gold='''import os
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
''',
    mutation=(
        "    try:\n        offset = stream.tell()\n    except (AttributeError, OSError):\n        return length\n    return length - offset\n",
        "    return length\n",
    ),
    tests='''import io
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
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_text_chunker",
    source="httpx/_decoders.py::TextChunker",
    problem_statement="""iter_text(chunk_size=...) returns one chunk short

```python
>>> c = TextChunker(chunk_size=2)
>>> c.decode("abcde")
['ab']
>>> c.flush()
['e']
```

`'cd'` is lost. Expected `['ab', 'cd']` then `['e']`.
""",
    gold='''import io
from typing import List, Optional


class TextChunker:
    """
    Handles returning text content in fixed-size chunks.
    """

    def __init__(self, chunk_size: Optional[int] = None) -> None:
        self._buffer = io.StringIO()
        self._chunk_size = chunk_size

    def decode(self, content: str) -> List[str]:
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

    def flush(self) -> List[str]:
        value = self._buffer.getvalue()
        self._buffer.seek(0)
        self._buffer.truncate()
        return [value] if value else []


class TextDecoder:
    """
    Handles incrementally decoding bytes into text
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        import codecs

        self.decoder = codecs.getincrementaldecoder(encoding)(errors="replace")

    def decode(self, data: bytes) -> str:
        return self.decoder.decode(data)

    def flush(self) -> str:
        return self.decoder.decode(b"", True)
''',
    mutation=(
        "                for i in range(0, len(value), self._chunk_size)\n            ]\n            if len(chunks[-1]) == self._chunk_size:\n                self._buffer.seek(0)\n                self._buffer.truncate()\n                return chunks\n            else:\n                self._buffer.seek(0)\n                self._buffer.write(chunks[-1])\n                self._buffer.truncate()\n                return chunks[:-1]\n",
        "                for i in range(0, len(value), self._chunk_size)\n            ]\n            if len(chunks[-1]) == self._chunk_size:\n                self._buffer.seek(0)\n                self._buffer.truncate()\n                return chunks\n            else:\n                self._buffer.seek(0)\n                self._buffer.write(chunks[-1])\n                self._buffer.truncate()\n                return chunks[:-2]\n",
    ),
    tests='''from src import TextChunker, TextDecoder


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
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_timeout",
    source="httpx/_config.py::Timeout",
    problem_statement="""Timeout(connect=5) with a default timeout ignores the default for other phases

```python
>>> t = Timeout(10.0, connect=5.0)
>>> t.read
None
```

Expected `10.0`. When a positional default is given, all unspecified phases should take it.
""",
    gold='''from typing import Optional, Union

TimeoutTypes = Union[float, None, "Timeout"]


class UnsetType:
    pass


UNSET = UnsetType()


class Timeout:
    """
    Timeout configuration.

    **Usage**:

    Timeout(None)               # No timeouts.
    Timeout(5.0)                # 5s timeout on all operations.
    Timeout(None, connect=5.0)  # 5s timeout on connect, no other timeouts.
    Timeout(5.0, connect=10.0)  # 10s timeout on connect. 5s timeout elsewhere.
    Timeout(5.0, pool=None)     # No timeout on acquiring connection from pool.
                                # 5s timeout elsewhere.
    """

    def __init__(
        self,
        timeout=UNSET,
        *,
        connect=UNSET,
        read=UNSET,
        write=UNSET,
        pool=UNSET,
    ) -> None:
        if isinstance(timeout, Timeout):
            # Passed as a single explicit Timeout.
            assert connect is UNSET
            assert read is UNSET
            assert write is UNSET
            assert pool is UNSET
            self.connect = timeout.connect
            self.read = timeout.read
            self.write = timeout.write
            self.pool = timeout.pool
        elif isinstance(timeout, tuple):
            # Passed as a tuple.
            self.connect = timeout[0]
            self.read = timeout[1]
            self.write = None if len(timeout) < 3 else timeout[2]
            self.pool = None if len(timeout) < 4 else timeout[3]
        elif not (
            isinstance(connect, UnsetType)
            or isinstance(read, UnsetType)
            or isinstance(write, UnsetType)
            or isinstance(pool, UnsetType)
        ):
            self.connect = connect
            self.read = read
            self.write = write
            self.pool = pool
        else:
            if isinstance(timeout, UnsetType):
                raise ValueError(
                    "httpx.Timeout must either include a default, or set all "
                    "four parameters explicitly."
                )
            self.connect = timeout if isinstance(connect, UnsetType) else connect
            self.read = timeout if isinstance(read, UnsetType) else read
            self.write = timeout if isinstance(write, UnsetType) else write
            self.pool = timeout if isinstance(pool, UnsetType) else pool

    def as_dict(self) -> dict:
        return {
            "connect": self.connect,
            "read": self.read,
            "write": self.write,
            "pool": self.pool,
        }

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.connect == other.connect
            and self.read == other.read
            and self.write == other.write
            and self.pool == other.pool
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        if len({self.connect, self.read, self.write, self.pool}) == 1:
            return f"{class_name}(timeout={self.connect})"
        return (
            f"{class_name}(connect={self.connect}, "
            f"read={self.read}, write={self.write}, pool={self.pool})"
        )
''',
    mutation=(
        "            self.read = timeout if isinstance(read, UnsetType) else read\n",
        "            self.read = None if isinstance(read, UnsetType) else read\n",
    ),
    tests='''import pytest
from src import Timeout


def test_default_applies_to_read():
    t = Timeout(10.0, connect=5.0)
    assert t.as_dict() == {"connect": 5.0, "read": 10.0, "write": 10.0, "pool": 10.0}


def test_single_value():
    assert Timeout(5.0).as_dict() == {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0}
    assert repr(Timeout(5.0)) == "Timeout(timeout=5.0)"


def test_none_default():
    assert Timeout(None, connect=5.0).read is None


def test_errors_and_copy():
    with pytest.raises(ValueError):
        Timeout(connect=1.0)
    assert Timeout(Timeout(3.0)) == Timeout(3.0)
''',
)

# ---------------------------------------------------------------------------
task(
    id="httpx_cookie_domain",
    source="httpx/_models.py (simplified)::Cookies.set / cookie domain match",
    problem_statement="""Cookies set for a parent domain are not sent to subdomains

A cookie set with `domain="example.com"` is sent to `example.com` but not to `api.example.com`. Per RFC 6265 a domain cookie should match the domain itself and all its subdomains. Cookies without a domain (host-only) should still match only the exact host.
""",
    gold='''from typing import Dict, List, Optional, Tuple


class Cookie:
    def __init__(self, name: str, value: str, domain: Optional[str] = None, path: str = "/") -> None:
        self.name = name
        self.value = value
        self.domain = domain.lstrip(".").lower() if domain else None
        self.path = path

    def domain_matches(self, host: str) -> bool:
        host = host.lower()
        if self.domain is None:
            return False  # host-only cookies are matched by the jar
        return host == self.domain or host.endswith("." + self.domain)

    def path_matches(self, path: str) -> bool:
        return path.startswith(self.path)


class Cookies:
    """A simple cookie jar keyed by (name, host-or-domain, path)."""

    def __init__(self) -> None:
        self._cookies: List[Tuple[Optional[str], Cookie]] = []

    def set(self, name: str, value: str, domain: Optional[str] = None, path: str = "/", host: Optional[str] = None) -> None:
        cookie = Cookie(name, value, domain=domain, path=path)
        self._cookies.append((None if domain else host, cookie))

    def for_request(self, host: str, path: str = "/") -> Dict[str, str]:
        out: Dict[str, str] = {}
        for host_only, cookie in self._cookies:
            if host_only is not None:
                if host_only.lower() != host.lower():
                    continue
            elif not cookie.domain_matches(host):
                continue
            if cookie.path_matches(path):
                out[cookie.name] = cookie.value
        return out
''',
    mutation=(
        '        return host == self.domain or host.endswith("." + self.domain)\n',
        '        return host == self.domain\n',
    ),
    tests='''from src import Cookies, Cookie


def test_subdomain_match():
    jar = Cookies()
    jar.set("sid", "1", domain="example.com")
    assert jar.for_request("api.example.com") == {"sid": "1"}
    assert jar.for_request("example.com") == {"sid": "1"}


def test_other_domain():
    jar = Cookies()
    jar.set("sid", "1", domain="example.com")
    assert jar.for_request("notexample.com") == {}


def test_host_only():
    jar = Cookies()
    jar.set("sid", "1", host="example.com")
    assert jar.for_request("example.com") == {"sid": "1"}
    assert jar.for_request("api.example.com") == {}


def test_path():
    jar = Cookies()
    jar.set("a", "1", domain="example.com", path="/admin")
    assert jar.for_request("example.com", "/") == {}
    assert jar.for_request("example.com", "/admin/x") == {"a": "1"}
    assert Cookie("n", "v", domain=".Example.com").domain == "example.com"
''',
)
