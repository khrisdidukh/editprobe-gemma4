from src import URL, same_origin, is_https_redirect, redirect_headers


def test_https_upgrade_keeps_auth():
    h = {"Authorization": "x", "Accept": "*/*"}
    assert redirect_headers(h, URL("http", "example.com"), URL("https", "example.com")) == h


def test_explicit_443():
    assert is_https_redirect(URL("http", "example.com"), URL("https", "example.com", 443))


def test_other_host_strips():
    h = {"Authorization": "x"}
    assert redirect_headers(h, URL("http", "a.com"), URL("http", "b.com")) == {}


def test_same_origin():
    assert same_origin(URL("https", "a.com"), URL("https", "a.com", 443))
    assert not same_origin(URL("http", "a.com"), URL("https", "a.com"))
