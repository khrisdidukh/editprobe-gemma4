from src import requote_uri, unquote_unreserved


def test_keeps_encoded_slash():
    assert requote_uri("http://example.com/a%2Fb") == "http://example.com/a%2Fb"


def test_unreserved_unescaped():
    assert unquote_unreserved("http://example.com/%7Euser") == "http://example.com/~user"


def test_quotes_illegal():
    assert requote_uri("http://example.com/a b") == "http://example.com/a%20b"


def test_invalid_escape():
    assert requote_uri("http://example.com/%zz") == "http://example.com/%25zz"
