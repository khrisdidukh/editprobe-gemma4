from src import prepend_scheme_if_needed


def test_port_kept():
    assert prepend_scheme_if_needed("example.com:8080/path", "http") == "http://example.com:8080/path"


def test_no_port():
    assert prepend_scheme_if_needed("example.com/path", "http") == "http://example.com/path"


def test_scheme_present():
    assert prepend_scheme_if_needed("https://example.com:443/x", "http") == "https://example.com:443/x"


def test_auth():
    assert prepend_scheme_if_needed("http://u:p@example.com:81/", "http") == "http://u:p@example.com:81/"
