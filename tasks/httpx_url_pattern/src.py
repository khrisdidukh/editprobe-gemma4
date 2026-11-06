import re
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
        self.scheme = "" if scheme in ("all", "http") else scheme
        self.host = "" if host == "*" else host
        self.port = port
        if not host or host.startswith("*"):
            # Any domain, or any domain matching a given suffix.
            self.host_regex: Optional[re.Pattern] = None
            if host and host.startswith("*"):
                domain = re.escape(host[2:])
                self.host_regex = re.compile(f"^.+\\.{domain}$")
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
