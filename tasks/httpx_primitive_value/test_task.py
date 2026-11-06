from src import primitive_value_to_str, encode_query_params


def test_bools():
    assert primitive_value_to_str(True) == "true"
    assert primitive_value_to_str(False) == "false"


def test_none_and_numbers():
    assert primitive_value_to_str(None) == ""
    assert primitive_value_to_str(1) == "1"
    assert primitive_value_to_str(1.5) == "1.5"


def test_query():
    assert encode_query_params({"a": True, "b": None, "c": "x"}) == "a=true&b=&c=x"
