import codecs
from src import guess_json_utf


def test_utf16_le_no_bom():
    assert guess_json_utf('{"a": 1}'.encode("utf-16-le")) == "utf-16-le"


def test_utf16_be_no_bom():
    assert guess_json_utf('{"a": 1}'.encode("utf-16-be")) == "utf-16-be"


def test_utf8():
    assert guess_json_utf(b'{"a": 1}') == "utf-8"


def test_bom():
    assert guess_json_utf(codecs.BOM_UTF8 + b'{}') == "utf-8-sig"
    assert guess_json_utf(codecs.BOM_UTF16_LE + "{}".encode("utf-16-le")) == "utf-16"


def test_utf32():
    assert guess_json_utf("{}".encode("utf-32-be")) == "utf-32-be"
    assert guess_json_utf("{}".encode("utf-32-le")) == "utf-32-le"
