from src import URLPattern, URL


def test_http_pattern_not_https():
    p = URLPattern("http://")
    assert p.matches(URL("http", "example.com"))
    assert not p.matches(URL("https", "example.com"))


def test_all():
    assert URLPattern("all://").matches(URL("https", "x.com"))


def test_host_port():
    p = URLPattern("https://example.com:8443")
    assert p.matches(URL("https", "example.com", 8443))
    assert not p.matches(URL("https", "example.com", 443))


def test_wildcard_and_priority():
    assert URLPattern("all://*.example.com").matches(URL("http", "a.example.com"))
    assert not URLPattern("all://*.example.com").matches(URL("http", "example.com"))
    assert URLPattern("http://example.com") < URLPattern("http://")
