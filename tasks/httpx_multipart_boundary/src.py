import re
from typing import Optional


def get_multipart_boundary_from_content_type(
    content_type: Optional[bytes],
) -> Optional[bytes]:
    if not content_type or not content_type.startswith(b"multipart/form-data"):
        return None
    # parse boundary according to
    # https://www.rfc-editor.org/rfc/rfc2046#section-5.1.1
    if b";" in content_type:
        for section in content_type.split(b";"):
            if section.strip().lower().startswith(b"boundary="):
                return section.strip()[len(b"boundary=") :]
    return None


def _format_form_param(name: str, value: str) -> bytes:
    """
    Encode a name/value pair within a multipart form.
    """

    def replacer(match: re.Match) -> str:
        return {"\\": "\\\\", '"': '\\"'}[match.group(0)]

    value = re.sub(r'["\\]', replacer, value)
    return f'{name}="{value}"'.encode()
