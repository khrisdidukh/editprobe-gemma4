from src import Cookies, Cookie


def test_subdomain_match():
    jar = Cookies()
    jar.set("sid", "1", domain="example.com")
    assert jar.for_request("api.example.com") == {"sid": "1"}
    assert jar.for_request("example.com") == {"sid": "1"}


def test_other_domain():
    jar = Cookies()
    jar.set("sid", "1", domain="example.com")
    assert jar.for_request("notexample.com") == {}


def test_host_only():
    jar = Cookies()
    jar.set("sid", "1", host="example.com")
    assert jar.for_request("example.com") == {"sid": "1"}
    assert jar.for_request("api.example.com") == {}


def test_path():
    jar = Cookies()
    jar.set("a", "1", domain="example.com", path="/admin")
    assert jar.for_request("example.com", "/") == {}
    assert jar.for_request("example.com", "/admin/x") == {"a": "1"}
    assert Cookie("n", "v", domain=".Example.com").domain == "example.com"
