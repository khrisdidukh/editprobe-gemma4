from src import ratio_distribute, ratio_reduce


def test_minimums():
    assert ratio_distribute(10, [1, 1], minimums=[8, 1]) == [8, 2]


def test_no_minimums():
    assert ratio_distribute(10, [1, 1]) == [5, 5]
    assert ratio_distribute(10, [1, 2]) == [4, 6]


def test_sum():
    out = ratio_distribute(17, [3, 1, 2], minimums=[1, 5, 1])
    assert sum(out) == 17 and out[1] >= 5


def test_reduce():
    assert ratio_reduce(20, [1, 1], [10, 10], [15, 15]) == [5, 5]
