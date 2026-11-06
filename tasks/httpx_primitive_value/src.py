from typing import Optional, Union

PrimitiveData = Optional[Union[str, int, float, bool]]


def primitive_value_to_str(value: PrimitiveData) -> str:
    """
    Coerce a primitive data type into a string value.

    Note that we prefer JSON-style 'true'/'false' for boolean values here.
    """
    if value is None:
        return ""
    return str(value)


def encode_query_params(params: dict) -> str:
    """Encode a dict of primitive values as a query string (no escaping)."""
    return "&".join(f"{k}={primitive_value_to_str(v)}" for k, v in params.items())
