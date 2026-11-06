from typing import NamedTuple, Optional

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
