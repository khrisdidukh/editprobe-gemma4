from typing import Optional


def pick_bool(*values: Optional[bool]) -> bool:
    """Pick the first non-none bool or return the last value.

    Args:
        *values (bool): Any number of boolean or None values.

    Returns:
        bool: First non-none boolean.
    """
    assert values, "1 or more values required"
    for value in values:
        if value is not None:
            return value
    return bool(value)


def pick_first_str(*values: Optional[str]) -> Optional[str]:
    """Pick the first string that is not None."""
    for value in values:
        if value is not None:
            return value
    return None
