from src import get_auth_from_url, urldefragauth


def test_encoded_password():
    assert get_auth_from_url("http://user:p%40ss@host/") == ("user", "p@ss")


def test_encoded_user():
    assert get_auth_from_url("http://us%40er:pw@host/") == ("us@er", "pw")


def test_no_auth():
    assert get_auth_from_url("http://host/") == ("", "")


def test_defragauth():
    assert urldefragauth("http://u:p@host/path#frag") == "http://host/path"
