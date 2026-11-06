"""Tasks adapted from psf/requests (Apache-2.0). Each task is a standalone module.

The `mutation` turns the gold module into the buggy module. Reversing it is the
minimal fix. Problem statements are written as a user would report the bug,
without naming the line.
"""

TASKS = []


def task(**kw):
    TASKS.append(kw)


# ---------------------------------------------------------------------------
task(
    id="req_parse_header_links",
    source="requests/utils.py::parse_header_links",
    problem_statement="""`parse_header_links` drops the last parameter of a link

When a Link header has several parameters, the last one is missing from the result:

```python
>>> parse_header_links('<http://example.com/page/2>; rel="next"; type="text/html"')
[{'url': 'http://example.com/page/2', 'rel': 'next'}]
```

I expected `'type': 'text/html'` to be in the dict as well. A header with a single parameter works fine.
""",
    gold='''import re


def parse_header_links(value: str) -> list[dict[str, str]]:
    """Return a list of parsed link headers.

    i.e. Link: <http:/.../front.jpeg>; rel=front; type="image/jpeg",<http://.../back.jpeg>; rel=back;type="image/jpeg"

    :rtype: list
    """

    links: list[dict[str, str]] = []

    replace_chars = " '\\""

    value = value.strip(replace_chars)
    if not value:
        return links

    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""

        link: dict[str, str] = {"url": url.strip("<> '\\"")}

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        links.append(link)

    return links
''',
    mutation=(
        '''        for param in params.split(";"):
            try:
                key, value = param.split("=")''',
        '''        for param in params.split(";")[:-1]:
            try:
                key, value = param.split("=")''',
    ),
    tests='''from src import parse_header_links


def test_two_params():
    out = parse_header_links('<http://example.com/page/2>; rel="next"; type="text/html"')
    assert out == [{"url": "http://example.com/page/2", "rel": "next", "type": "text/html"}]


def test_single_param():
    out = parse_header_links("<http://example.com/a>; rel=front")
    assert out == [{"url": "http://example.com/a", "rel": "front"}]


def test_multiple_links():
    out = parse_header_links('<http://a/1>; rel=next, <http://a/2>; rel=last')
    assert out == [{"url": "http://a/1", "rel": "next"}, {"url": "http://a/2", "rel": "last"}]


def test_empty():
    assert parse_header_links("") == []
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_parse_dict_header",
    source="requests/utils.py::parse_dict_header",
    problem_statement="""parse_dict_header mangles values that contain '='

```python
>>> parse_dict_header('token="abc=="')
{'token': 'abc'}
```

Base64-padded values lose their trailing `==`. Expected `{'token': 'abc=='}`. Keys without values still return None, which is fine.
""",
    gold='''import re

_quoted_string_re = re.compile(r'"(?:[^"\\\\]|\\\\.)*"|[^,]+')


def _parse_list_header(value: str) -> list[str]:
    """Split a comma separated header, keeping quoted strings intact."""
    items = []
    for m in _quoted_string_re.finditer(value):
        item = m.group(0).strip()
        if item:
            items.append(item)
    return items


def unquote_header_value(value: str) -> str:
    """Unquote a header value the way browsers do it."""
    if value and value[0] == value[-1] == '"':
        value = value[1:-1]
        return value.replace("\\\\\\\\", "\\\\").replace('\\\\"', '"')
    return value


def parse_dict_header(value: str) -> dict:
    """Parse lists of key, value pairs as described by RFC 2068 Section 2 and
    convert them into a python dict:

    >>> d = parse_dict_header('foo="is a fish", bar="as well"')
    >>> sorted(d.items())
    [('bar', 'as well'), ('foo', 'is a fish')]

    If there is no value for a key it will be `None`:

    >>> parse_dict_header('key_without_value')
    {'key_without_value': None}
    """
    result: dict = {}
    for item in _parse_list_header(value):
        if "=" not in item:
            result[item] = None
            continue
        name, value = item.split("=", 1)
        if value[:1] == value[-1:] == '"':
            value = unquote_header_value(value)
        result[name] = value
    return result
''',
    mutation=(
        '        name, value = item.split("=", 1)\n',
        '        name, value = item.split("=")[:2]\n',
    ),
    tests='''import pytest
from src import parse_dict_header


def test_value_with_equals():
    assert parse_dict_header('token="abc=="') == {"token": "abc=="}


def test_plain():
    d = parse_dict_header('foo="is a fish", bar="as well"')
    assert sorted(d.items()) == [("bar", "as well"), ("foo", "is a fish")]


def test_no_value():
    assert parse_dict_header("key_without_value") == {"key_without_value": None}


def test_unquoted_equals():
    assert parse_dict_header("a=b=c") == {"a": "b=c"}
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_case_insensitive_dict",
    source="requests/structures.py::CaseInsensitiveDict",
    problem_statement="""CaseInsensitiveDict: deleting a key with different case raises KeyError

```python
>>> d = CaseInsensitiveDict()
>>> d['Content-Type'] = 'text/html'
>>> 'content-type' in d
True
>>> del d['content-type']
KeyError: 'content-type'
```

Lookup and `in` are case-insensitive but deletion is not.
""",
    gold='''from collections.abc import Mapping, MutableMapping


class CaseInsensitiveDict(MutableMapping):
    """A case-insensitive ``dict``-like object.

    Implements all methods and operations of ``MutableMapping`` as well as
    dict's ``copy``. Also provides ``lower_items``.

    All keys are expected to be strings. The structure remembers the case of
    the last key to be set, and ``iter(instance)``, ``keys()``, ``items()``,
    ``iterkeys()``, and ``iteritems()`` will contain case-sensitive keys.
    However, querying and contains testing is case insensitive.
    """

    def __init__(self, data=None, **kwargs):
        self._store = {}
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return ((lowerkey, keyval[1]) for (lowerkey, keyval) in self._store.items())

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))
''',
    mutation=(
        "    def __delitem__(self, key):\n        del self._store[key.lower()]\n",
        "    def __delitem__(self, key):\n        del self._store[key]\n",
    ),
    tests='''import pytest
from src import CaseInsensitiveDict


def test_delete_other_case():
    d = CaseInsensitiveDict()
    d["Content-Type"] = "text/html"
    del d["content-type"]
    assert len(d) == 0


def test_delete_same_case():
    d = CaseInsensitiveDict({"Accept": "*/*"})
    del d["Accept"]
    assert "accept" not in d


def test_lookup():
    d = CaseInsensitiveDict({"Accept": "*/*"})
    assert d["ACCEPT"] == "*/*"
    assert list(d) == ["Accept"]


def test_eq():
    assert CaseInsensitiveDict({"a": 1}) == {"A": 1}
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_guess_json_utf",
    source="requests/utils.py::guess_json_utf",
    problem_statement="""guess_json_utf returns None for UTF-16-LE JSON without BOM

```python
>>> guess_json_utf('{"a": 1}'.encode('utf-16-le'))
>>>
```

Returns None, so the response body cannot be decoded. UTF-16-BE without BOM is detected correctly as 'utf-16-be'. Expected 'utf-16-le'.
""",
    gold='''import codecs

# Null bytes; no need to recreate these on each call to guess_json_utf
_null = "\\x00".encode("ascii")  # encoding to ASCII for Python 3
_null2 = _null * 2
_null3 = _null * 3


def guess_json_utf(data: bytes):
    """Guess the encoding of a JSON byte string from its first bytes.

    :rtype: str
    """
    # JSON always starts with two ASCII characters, so detection is as
    # easy as counting the nulls and from their location and count
    # determine the encoding. Also detect a BOM, if present.
    sample = data[:4]
    if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
        return "utf-32"  # BOM included
    if sample[:3] == codecs.BOM_UTF8:
        return "utf-8-sig"  # BOM included, MS style (discouraged)
    if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return "utf-16"  # BOM included
    nullcount = sample.count(_null)
    if nullcount == 0:
        return "utf-8"
    if nullcount == 2:
        if sample[::2] == _null2:  # 1st and 3rd are null
            return "utf-16-be"
        if sample[1::2] == _null2:  # 2nd and 4th are null
            return "utf-16-le"
        # Did not detect 2 valid UTF-16 ascii-range characters
    if nullcount == 3:
        if sample[:3] == _null3:
            return "utf-32-be"
        if sample[1:] == _null3:
            return "utf-32-le"
        # Did not detect a valid UTF-32 ascii-range character
    return None
''',
    mutation=(
        '        if sample[1::2] == _null2:  # 2nd and 4th are null\n',
        '        if sample[1::3] == _null2:  # 2nd and 4th are null\n',
    ),
    tests='''import codecs
from src import guess_json_utf


def test_utf16_le_no_bom():
    assert guess_json_utf('{"a": 1}'.encode("utf-16-le")) == "utf-16-le"


def test_utf16_be_no_bom():
    assert guess_json_utf('{"a": 1}'.encode("utf-16-be")) == "utf-16-be"


def test_utf8():
    assert guess_json_utf(b'{"a": 1}') == "utf-8"


def test_bom():
    assert guess_json_utf(codecs.BOM_UTF8 + b'{}') == "utf-8-sig"
    assert guess_json_utf(codecs.BOM_UTF16_LE + "{}".encode("utf-16-le")) == "utf-16"


def test_utf32():
    assert guess_json_utf("{}".encode("utf-32-be")) == "utf-32-be"
    assert guess_json_utf("{}".encode("utf-32-le")) == "utf-32-le"
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_dotted_netmask",
    source="requests/utils.py::dotted_netmask, address_in_network",
    problem_statement="""address_in_network gives wrong answers for /24 networks

```python
>>> address_in_network('192.168.1.1', '192.168.1.0/24')
False
>>> dotted_netmask(24)
'255.255.254.0'
```

The netmask for /24 should be 255.255.255.0 and the address should be reported as inside the network.
""",
    gold='''import socket
import struct


def dotted_netmask(mask: int) -> str:
    """Converts mask from /xx format to xxx.xxx.xxx.xxx

    Example: if mask is 24 function returns 255.255.255.0

    :rtype: str
    """
    bits = 0xFFFFFFFF ^ (1 << 32 - mask) - 1
    return socket.inet_ntoa(struct.pack(">I", bits))


def address_in_network(ip: str, net: str) -> bool:
    """This function allows you to check if an IP belongs to a network subnet

    Example: returns True if ip = 192.168.1.1 and net = 192.168.1.0/24
             returns False if ip = 192.168.1.1 and net = 192.168.100.0/24

    :rtype: bool
    """
    ipaddr = struct.unpack("=L", socket.inet_aton(ip))[0]
    netaddr, bits = net.split("/")
    netmask = struct.unpack("=L", socket.inet_aton(dotted_netmask(int(bits))))[0]
    network = struct.unpack("=L", socket.inet_aton(netaddr))[0] & netmask
    return (ipaddr & netmask) == (network & netmask)


def is_ipv4_address(string_ip: str) -> bool:
    """
    :rtype: bool
    """
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True
''',
    mutation=(
        "    bits = 0xFFFFFFFF ^ (1 << 32 - mask) - 1\n",
        "    bits = 0xFFFFFFFF ^ (1 << 33 - mask) - 1\n",
    ),
    tests='''from src import dotted_netmask, address_in_network, is_ipv4_address


def test_netmask_24():
    assert dotted_netmask(24) == "255.255.255.0"


def test_netmask_other():
    assert dotted_netmask(8) == "255.0.0.0"
    assert dotted_netmask(25) == "255.255.255.128"


def test_in_network():
    assert address_in_network("192.168.1.1", "192.168.1.0/24")
    assert not address_in_network("192.168.1.1", "192.168.100.0/24")


def test_is_ipv4():
    assert is_ipv4_address("8.8.8.8")
    assert not is_ipv4_address("localhost")
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_unquote_unreserved",
    source="requests/utils.py::unquote_unreserved, requote_uri",
    problem_statement="""requote_uri un-escapes reserved characters

```python
>>> requote_uri('http://example.com/a%2Fb')
'http://example.com/a/b'
```

`%2F` is an escaped slash and must stay escaped, otherwise the path changes meaning. Unreserved characters such as `%7E` should still be un-escaped to `~`.
""",
    gold='''from urllib.parse import quote

UNRESERVED_SET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" + "0123456789-._~"
)


class InvalidURL(ValueError):
    pass


def unquote_unreserved(uri: str) -> str:
    """Un-escape any percent-escape sequences in a URI that are unreserved
    characters. This leaves all reserved, illegal and non-ASCII bytes encoded.

    :rtype: str
    """
    parts = uri.split("%")
    for i in range(1, len(parts)):
        h = parts[i][0:2]
        if len(h) == 2 and h.isalnum():
            try:
                c = chr(int(h, 16))
            except ValueError:
                raise InvalidURL(f"Invalid percent-escape sequence: '{h}'")

            if c in UNRESERVED_SET:
                parts[i] = c + parts[i][2:]
            else:
                parts[i] = f"%{parts[i]}"
        else:
            parts[i] = f"%{parts[i]}"
    return "".join(parts)


def requote_uri(uri: str) -> str:
    """Re-quote the given URI.

    This function passes the given URI through an unquote/quote cycle to
    ensure that it is fully and consistently quoted.

    :rtype: str
    """
    safe_with_percent = "!#$%&'()*+,/:;=?@[]~"
    safe_without_percent = "!#$&'()*+,/:;=?@[]~"
    try:
        # Unquote only the unreserved characters
        # Then quote only illegal characters (do not quote reserved,
        # unreserved, or '%')
        return quote(unquote_unreserved(uri), safe=safe_with_percent)
    except InvalidURL:
        # We couldn't unquote the given URI, so let's try quoting it, but
        # there may be unquoted '%'s in the URI. We need to make sure they're
        # properly quoted so they do not cause issues elsewhere.
        return quote(uri, safe=safe_without_percent)
''',
    mutation=(
        "            if c in UNRESERVED_SET:\n                parts[i] = c + parts[i][2:]\n            else:\n                parts[i] = f\"%{parts[i]}\"\n",
        "            if c in UNRESERVED_SET or c == \"/\":\n                parts[i] = c + parts[i][2:]\n            else:\n                parts[i] = f\"%{parts[i]}\"\n",
    ),
    tests='''from src import requote_uri, unquote_unreserved


def test_keeps_encoded_slash():
    assert requote_uri("http://example.com/a%2Fb") == "http://example.com/a%2Fb"


def test_unreserved_unescaped():
    assert unquote_unreserved("http://example.com/%7Euser") == "http://example.com/~user"


def test_quotes_illegal():
    assert requote_uri("http://example.com/a b") == "http://example.com/a%20b"


def test_invalid_escape():
    assert requote_uri("http://example.com/%zz") == "http://example.com/%25zz"
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_get_auth_from_url",
    source="requests/utils.py::get_auth_from_url",
    problem_statement="""Credentials with percent-encoded characters are sent wrong

When the URL contains an encoded password, e.g. `http://user:p%40ss@host/`, the password sent is `p%40ss` instead of `p@ss`. The username is decoded correctly. So only the password is left encoded.
""",
    gold='''from urllib.parse import unquote, urlparse


def get_auth_from_url(url: str) -> tuple:
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        auth = (unquote(parsed.username), unquote(parsed.password))
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth


def urldefragauth(url: str) -> str:
    """Given a url remove the fragment and the authentication part.

    :rtype: str
    """
    scheme, netloc, path, params, query, fragment = __import__("urllib.parse").parse.urlparse(url)

    # see func:`prepend_scheme_if_needed`
    if not netloc:
        netloc, path = path, netloc

    netloc = netloc.rsplit("@", 1)[-1]

    from urllib.parse import urlunparse

    return urlunparse((scheme, netloc, path, params, query, ""))
''',
    mutation=(
        "        auth = (unquote(parsed.username), unquote(parsed.password))\n",
        "        auth = (unquote(parsed.username), parsed.password)\n",
    ),
    tests='''from src import get_auth_from_url, urldefragauth


def test_encoded_password():
    assert get_auth_from_url("http://user:p%40ss@host/") == ("user", "p@ss")


def test_encoded_user():
    assert get_auth_from_url("http://us%40er:pw@host/") == ("us@er", "pw")


def test_no_auth():
    assert get_auth_from_url("http://host/") == ("", "")


def test_defragauth():
    assert urldefragauth("http://u:p@host/path#frag") == "http://host/path"
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_iter_slices",
    source="requests/utils.py::iter_slices",
    problem_statement="""iter_slices skips the tail of the string

```python
>>> list(iter_slices("abcdefg", 3))
['abc', 'def']
```

The final `'g'` is missing. Every byte of the body must be yielded.
""",
    gold='''def iter_slices(string, slice_length):
    """Iterate over slices of a string."""
    pos = 0
    if slice_length is None or slice_length <= 0:
        slice_length = len(string)
    while pos < len(string):
        yield string[pos : pos + slice_length]
        pos += slice_length


def to_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. If it can be, return a list of tuples, e.g.,

    ::

        >>> to_key_val_list([('key', 'val')])
        [('key', 'val')]
        >>> to_key_val_list({'key': 'val'})
        [('key', 'val')]
        >>> to_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples

    :rtype: list
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    if hasattr(value, "items"):
        value = value.items()

    return list(value)
''',
    mutation=(
        "    while pos < len(string):\n",
        "    while pos + slice_length <= len(string):\n",
    ),
    tests='''import pytest
from src import iter_slices, to_key_val_list


def test_tail_kept():
    assert list(iter_slices("abcdefg", 3)) == ["abc", "def", "g"]


def test_exact():
    assert list(iter_slices("abcdef", 3)) == ["abc", "def"]


def test_none_length():
    assert list(iter_slices("abc", None)) == ["abc"]


def test_key_val_list():
    assert to_key_val_list({"k": "v"}) == [("k", "v")]
    with pytest.raises(ValueError):
        to_key_val_list("string")
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_get_encoding_from_headers",
    source="requests/utils.py::get_encoding_from_headers",
    problem_statement="""Charset from Content-Type is ignored

```python
>>> get_encoding_from_headers({'content-type': 'text/html; charset=iso-8859-1'})
'ISO-8859-1'
```

That is the fallback value for `text/*`, not the charset the server sent. A header like `application/json; charset=utf-16` also returns `utf-8`. The charset parameter should win.
""",
    gold='''def _parse_content_type_header(header: str):
    """Returns content type and parameters from given header

    :param header: string
    :return: tuple containing content type and dictionary of
         parameters
    """

    tokens = header.split(";")
    content_type, params = tokens[0].strip(), tokens[1:]
    params_dict = {}
    items_to_strip = "\\"' "

    for param in params:
        param = param.strip()
        if param:
            key, value = param, True
            index_of_equals = param.find("=")
            if index_of_equals != -1:
                key = param[:index_of_equals].strip(items_to_strip)
                value = param[index_of_equals + 1 :].strip(items_to_strip)
            params_dict[key.lower()] = value
    return content_type, params_dict


def get_encoding_from_headers(headers):
    """Returns encodings from given HTTP Header Dict.

    :param headers: dictionary to extract encoding from.
    :rtype: str
    """

    content_type = headers.get("content-type")

    if not content_type:
        return None

    content_type, params = _parse_content_type_header(content_type)

    if "charset" in params:
        return params["charset"].strip("'\\"")

    if "text" in content_type:
        return "ISO-8859-1"

    if "application/json" in content_type:
        # Assume UTF-8 based on RFC 4627: https://www.ietf.org/rfc/rfc4627.txt since the charset was unset
        return "utf-8"

    return None
''',
    mutation=(
        "            params_dict[key.lower()] = value\n",
        "            params_dict[key] = value.lower()\n",
    ),
    tests='''from src import get_encoding_from_headers, _parse_content_type_header


def test_charset_wins():
    assert get_encoding_from_headers({"content-type": "text/html; charset=iso-8859-1"}) == "iso-8859-1"
    assert get_encoding_from_headers({"content-type": "application/json; charset=utf-16"}) == "utf-16"


def test_charset_key_case():
    assert get_encoding_from_headers({"content-type": "text/html; Charset=UTF-8"}) == "UTF-8"


def test_fallbacks():
    assert get_encoding_from_headers({"content-type": "text/plain"}) == "ISO-8859-1"
    assert get_encoding_from_headers({"content-type": "application/json"}) == "utf-8"
    assert get_encoding_from_headers({"content-type": "image/png"}) is None
    assert get_encoding_from_headers({}) is None


def test_parse_params():
    ct, params = _parse_content_type_header('multipart/form-data; boundary="XyZ"')
    assert ct == "multipart/form-data"
    assert params == {"boundary": "XyZ"}
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_prepend_scheme",
    source="requests/utils.py::prepend_scheme_if_needed",
    problem_statement="""prepend_scheme_if_needed loses the port

```python
>>> prepend_scheme_if_needed('example.com:8080/path', 'http')
'http://example.com/path'
```

The `:8080` disappears. URLs that already have a scheme are returned unchanged, which is correct.
""",
    gold='''import re
from urllib.parse import urlunparse

_URL_RE = re.compile(
    r"^(?:(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)://)?"
    r"(?:(?P<auth>[^@/]*)@)?"
    r"(?P<host>\\[[^\\]]*\\]|[^:/?#]*)"
    r"(?::(?P<port>\\d*))?"
    r"(?P<path>/[^?#]*)?"
    r"(?:\\?(?P<query>[^#]*))?"
    r"(?:#(?P<fragment>.*))?$"
)


def parse_url(url: str):
    """Small url splitter returning (scheme, auth, host, port, path, query, fragment)."""
    m = _URL_RE.match(url)
    if m is None:
        raise ValueError(f"cannot parse url {url!r}")
    g = m.groupdict()
    port = int(g["port"]) if g["port"] else None
    return g["scheme"], g["auth"], g["host"] or None, port, g["path"], g["query"], g["fragment"]


def prepend_scheme_if_needed(url: str, new_scheme: str) -> str:
    """Given a URL that may or may not have a scheme, prepend the given scheme.
    Does not replace a present scheme with the one provided as an argument.

    :rtype: str
    """
    scheme, auth, host, port, path, query, fragment = parse_url(url)

    if auth:
        # parse_url doesn't provide the netloc with auth
        # so we'll add it ourselves.
        host = "@".join([auth, host])
    if port:
        host = f"{host}:{port}"
    if scheme is None:
        scheme = new_scheme
    if path is None:
        path = ""

    return urlunparse((scheme, host, path, "", query or "", fragment or ""))
''',
    mutation=(
        "    if port:\n        host = f\"{host}:{port}\"\n    if scheme is None:\n",
        "    if scheme is None:\n",
    ),
    tests='''from src import prepend_scheme_if_needed


def test_port_kept():
    assert prepend_scheme_if_needed("example.com:8080/path", "http") == "http://example.com:8080/path"


def test_no_port():
    assert prepend_scheme_if_needed("example.com/path", "http") == "http://example.com/path"


def test_scheme_present():
    assert prepend_scheme_if_needed("https://example.com:443/x", "http") == "https://example.com:443/x"


def test_auth():
    assert prepend_scheme_if_needed("http://u:p@example.com:81/", "http") == "http://u:p@example.com:81/"
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_check_header_validity",
    source="requests/utils.py::check_header_validity",
    problem_statement="""Header values with leading whitespace are accepted

`check_header_validity(("X-Test", " value"))` should raise `InvalidHeader` (leading whitespace in a header value is rejected to prevent header injection), but it passes silently. Header *names* with spaces are still rejected properly.
""",
    gold='''import re


class InvalidHeader(ValueError):
    """The header value provided was somehow invalid."""


# Ensure that ':' does not appear in the header name and that the value does
# not start with whitespace or contain a newline. Keep it simple but strict.
_HEADER_VALIDATORS_STR = (
    re.compile(r"^[^:\\s][^:\\r\\n]*$"),  # name
    re.compile(r"^\\S[^\\r\\n]*$|^$"),  # value
)
_HEADER_VALIDATORS_BYTE = (
    re.compile(rb"^[^:\\s][^:\\r\\n]*$"),
    re.compile(rb"^\\S[^\\r\\n]*$|^$"),
)
HEADER_VALIDATORS = {
    bytes: _HEADER_VALIDATORS_BYTE,
    str: _HEADER_VALIDATORS_STR,
}


def check_header_validity(header) -> None:
    """Verifies that header parts don't contain leading whitespace
    reserved characters, or return characters.

    :param header: tuple, in the format (name, value).
    """
    name, value = header
    _validate_header_part(header, name, 0)
    _validate_header_part(header, value, 1)


def _validate_header_part(header, header_part, header_validator_index: int) -> None:
    if isinstance(header_part, str):
        validator = _HEADER_VALIDATORS_STR[header_validator_index]
    elif isinstance(header_part, bytes):
        validator = _HEADER_VALIDATORS_BYTE[header_validator_index]
    else:
        raise InvalidHeader(
            f"Header part ({header_part!r}) from {header} "
            f"must be of type str or bytes, not {type(header_part)}"
        )

    if not validator.match(header_part):
        header_kind = "name" if header_validator_index == 0 else "value"
        raise InvalidHeader(
            f"Invalid leading whitespace, reserved character(s), or return "
            f"character(s) in header {header_kind}: {header_part!r}"
        )
''',
    mutation=(
        "    _validate_header_part(header, name, 0)\n    _validate_header_part(header, value, 1)\n",
        "    _validate_header_part(header, name, 0)\n    _validate_header_part(header, value, 0)\n",
    ),
    tests='''import pytest
from src import check_header_validity, InvalidHeader


def test_leading_space_value_rejected():
    with pytest.raises(InvalidHeader):
        check_header_validity(("X-Test", " value"))


def test_colon_in_value_ok():
    check_header_validity(("Host", "example.com:8080"))


def test_newline_rejected():
    with pytest.raises(InvalidHeader):
        check_header_validity(("X-Test", "a\\r\\nb"))


def test_bad_name():
    with pytest.raises(InvalidHeader):
        check_header_validity((" X-Test", "v"))
    with pytest.raises(InvalidHeader):
        check_header_validity(("X:Test", "v"))


def test_bytes_ok():
    check_header_validity((b"X-Test", b"v"))
''',
)

# ---------------------------------------------------------------------------
task(
    id="req_super_len",
    source="requests/utils.py::super_len",
    problem_statement="""Content-Length wrong for file objects not at position 0

If I open a file, read part of it, and pass the object as the body, the computed length is the whole file size, not the remaining bytes:

```python
>>> f = io.BytesIO(b"0123456789")
>>> f.read(4)
>>> super_len(f)
10
```

Expected 6. The server then waits for 4 bytes that never come.
""",
    gold='''import io
import os


def super_len(o) -> int:
    """Best-effort length of a body object (str, bytes, file-like, ...)."""
    total_length = None
    current_position = 0

    if isinstance(o, str):
        o = o.encode("utf-8")

    if hasattr(o, "__len__"):
        total_length = len(o)

    elif hasattr(o, "len"):
        total_length = o.len

    elif hasattr(o, "fileno"):
        try:
            fileno = o.fileno()
        except (io.UnsupportedOperation, AttributeError):
            # AttributeError is a surprising exception, seeing as how we've just checked
            # that `hasattr(o, 'fileno')`.  It happens for objects obtained via
            # `Tarfile.extractfile()`, per issue 5229.
            pass
        else:
            total_length = os.fstat(fileno).st_size

    if hasattr(o, "tell"):
        try:
            current_position = o.tell()
        except OSError:
            # This can happen in some weird situations, such as when the file
            # is actually a special file descriptor like stdin.
            if total_length is not None:
                current_position = total_length
        else:
            if hasattr(o, "seek") and total_length is None:
                # StringIO and BytesIO have seek but no usable fileno
                try:
                    # seek to end of file
                    o.seek(0, 2)
                    total_length = o.tell()

                    # seek back to current position to support
                    # partially read file-like objects
                    o.seek(current_position or 0)
                except OSError:
                    total_length = 0

    if total_length is None:
        total_length = 0

    return max(0, total_length - current_position)
''',
    mutation=(
        "    return max(0, total_length - current_position)\n",
        "    return max(0, total_length)\n",
    ),
    tests='''import io
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
''',
)
