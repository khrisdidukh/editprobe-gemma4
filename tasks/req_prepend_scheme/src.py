import re
from urllib.parse import urlunparse

_URL_RE = re.compile(
    r"^(?:(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)://)?"
    r"(?:(?P<auth>[^@/]*)@)?"
    r"(?P<host>\[[^\]]*\]|[^:/?#]*)"
    r"(?::(?P<port>\d*))?"
    r"(?P<path>/[^?#]*)?"
    r"(?:\?(?P<query>[^#]*))?"
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
    if scheme is None:
        scheme = new_scheme
    if path is None:
        path = ""

    return urlunparse((scheme, host, path, "", query or "", fragment or ""))
