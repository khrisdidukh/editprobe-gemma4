import re

_quoted_string_re = re.compile(r'"(?:[^"\\]|\\.)*"|[^,]+')


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
        return value.replace("\\\\", "\\").replace('\\"', '"')
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
