from typing import Iterable, Iterator, Tuple, Union

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
    return "\n".join(f"{k}: {v}" for k, v in obfuscate_sensitive_headers(items))
