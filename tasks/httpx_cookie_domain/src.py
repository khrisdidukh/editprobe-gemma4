from typing import Dict, List, Optional, Tuple


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
        return host == self.domain

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
