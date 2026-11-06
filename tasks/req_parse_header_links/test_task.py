from src import parse_header_links


def test_two_params():
    out = parse_header_links('<http://example.com/page/2>; rel="next"; type="text/html"')
    assert out == [{"url": "http://example.com/page/2", "rel": "next", "type": "text/html"}]


def test_single_param():
    out = parse_header_links("<http://example.com/a>; rel=front")
    assert out == [{"url": "http://example.com/a", "rel": "front"}]


def test_multiple_links():
    out = parse_header_links('<http://a/1>; rel=next, <http://a/2>; rel=last')
    assert out == [{"url": "http://a/1", "rel": "next"}, {"url": "http://a/2", "rel": "last"}]


def test_empty():
    assert parse_header_links("") == []
