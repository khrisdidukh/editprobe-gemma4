from src import get_multipart_boundary_from_content_type, _format_form_param


def test_quoted():
    assert get_multipart_boundary_from_content_type(b'multipart/form-data; boundary="abc123"') == b"abc123"


def test_unquoted():
    assert get_multipart_boundary_from_content_type(b"multipart/form-data; boundary=abc123") == b"abc123"


def test_none():
    assert get_multipart_boundary_from_content_type(b"application/json") is None
    assert get_multipart_boundary_from_content_type(None) is None
    assert get_multipart_boundary_from_content_type(b"multipart/form-data") is None


def test_form_param():
    assert _format_form_param("name", 'a"b') == b'name="a\\"b"'
