from src import obfuscate_sensitive_headers, format_headers


def test_proxy_auth_hidden():
    out = dict(obfuscate_sensitive_headers([("Proxy-Authorization", "Basic abc")]))
    assert out == {"Proxy-Authorization": "[secure]"}


def test_auth_hidden():
    out = dict(obfuscate_sensitive_headers([("Authorization", "Bearer x")]))
    assert out == {"Authorization": "[secure]"}


def test_bytes():
    out = dict(obfuscate_sensitive_headers([(b"authorization", b"x")]))
    assert out == {b"authorization": b"[secure]"}


def test_others_untouched():
    assert format_headers([("Host", "example.com"), ("Authorization", "x")]) == "Host: example.com\nAuthorization: [secure]"
