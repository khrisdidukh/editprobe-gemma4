import re


class InvalidHeader(ValueError):
    """The header value provided was somehow invalid."""


# Ensure that ':' does not appear in the header name and that the value does
# not start with whitespace or contain a newline. Keep it simple but strict.
_HEADER_VALIDATORS_STR = (
    re.compile(r"^[^:\s][^:\r\n]*$"),  # name
    re.compile(r"^\S[^\r\n]*$|^$"),  # value
)
_HEADER_VALIDATORS_BYTE = (
    re.compile(rb"^[^:\s][^:\r\n]*$"),
    re.compile(rb"^\S[^\r\n]*$|^$"),
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
    _validate_header_part(header, value, 0)


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
