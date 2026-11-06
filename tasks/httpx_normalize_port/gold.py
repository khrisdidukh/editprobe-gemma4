from typing import Optional, Union


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
