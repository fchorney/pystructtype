from pystructtype.utils import int_to_bool_list, list_chunks


def test_list_chunks():
    data = [1, 2, 3, 4, 5, 6]

    assert list(list_chunks(data, 2)) == [[1, 2], [3, 4], [5, 6]]
    assert list(list_chunks(data, 3)) == [[1, 2, 3], [4, 5, 6]]
    assert list(list_chunks(data, 4)) == [[1, 2, 3, 4], [5, 6]]


def test_int_to_bool_list():
    assert int_to_bool_list(ord("A"), 1) == [True, False, False, False, False, False, True, False]
    assert int_to_bool_list([ord("A"), ord("B")], 2) == [
        False,
        True,
        False,
        False,
        False,
        False,
        True,
        False,
        True,
        False,
        False,
        False,
        False,
        False,
        True,
        False,
    ]
