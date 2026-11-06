from src import get_encoding_from_headers, _parse_content_type_header


def test_charset_wins():
    assert get_encoding_from_headers({"content-type": "text/html; charset=iso-8859-1"}) == "iso-8859-1"
    assert get_encoding_from_headers({"content-type": "application/json; charset=utf-16"}) == "utf-16"


def test_charset_key_case():
    assert get_encoding_from_headers({"content-type": "text/html; Charset=UTF-8"}) == "UTF-8"


def test_fallbacks():
    assert get_encoding_from_headers({"content-type": "text/plain"}) == "ISO-8859-1"
    assert get_encoding_from_headers({"content-type": "application/json"}) == "utf-8"
    assert get_encoding_from_headers({"content-type": "image/png"}) is None
    assert get_encoding_from_headers({}) is None


def test_parse_params():
    ct, params = _parse_content_type_header('multipart/form-data; boundary="XyZ"')
    assert ct == "multipart/form-data"
    assert params == {"boundary": "XyZ"}
