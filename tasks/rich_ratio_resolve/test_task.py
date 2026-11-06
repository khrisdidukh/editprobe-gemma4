from src import ratio_resolve, Edge


def test_fixed_plus_flexible():
    assert ratio_resolve(10, [Edge(size=3), Edge(ratio=1)]) == [3, 7]


def test_two_flexible():
    assert ratio_resolve(10, [Edge(ratio=1), Edge(ratio=1)]) == [5, 5]


def test_minimum():
    assert ratio_resolve(10, [Edge(size=8), Edge(ratio=1, minimum_size=3)]) == [8, 3]


def test_rounding():
    assert sum(ratio_resolve(10, [Edge(ratio=1), Edge(ratio=1), Edge(ratio=1)])) == 10
