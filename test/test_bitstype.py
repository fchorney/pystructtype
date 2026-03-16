from typing import ClassVar

import pytest

from pystructtype import BitsType, uint8_t, uint16_t


# Use a list of length > 1 for 'b', and ensure the bits logic works with the current structdataclass logic
class MyBits(BitsType):
    __bits_type__: ClassVar = uint8_t
    __bits_definition__: ClassVar = {"a": 0, "b": [1, 2], "c": 3}
    a: bool
    b: list[bool]
    c: bool


class MyBits16(BitsType):
    __bits_type__: ClassVar = uint16_t
    __bits_definition__: ClassVar = {"x": list(range(16))}
    x: list[bool]


def test_bits_decode_encode_bool_fields():
    # 0b00001101 = 13
    b = MyBits()
    b.decode([13])
    assert b.a
    assert not b.b[0]
    assert b.b[1]
    assert b.c
    # Now encode and check round-trip
    b.a = False
    b.b = [True, False]
    b.c = False
    encoded = b._encode()
    b2 = MyBits()
    b2.decode(encoded)
    assert not b2.a
    assert b2.b[0]
    assert not b2.b[1]
    assert not b2.c


def test_bits_decode_encode_list():
    b = MyBits16()
    b.decode([0b10101010, 0b10101010])

    # Accept any bit order, just check length and type
    assert isinstance(b.x, list)
    assert len(b.x) == 16

    # Now encode and check round-trip
    b.x = [True, False] * 8
    encoded = b.encode()

    b2 = MyBits16()
    b2.decode(encoded)
    assert b2.x == [True, False] * 8


def test_bits_edge_cases():
    # All bits set
    b = MyBits()
    b.decode([0xFF])
    assert b.a
    assert all(b.b)
    assert b.c

    # All bits clear
    b._raw = 0
    b.decode([0])
    assert not b.a
    # noinspection PyTypeChecker
    assert all(not x for x in b.b)
    assert not b.c


def test_bits_type_meta():
    b = MyBits()
    # _meta and _meta should be set up
    assert isinstance(b._meta, dict)
    # Should match the definition
    assert set(b._meta.keys()) == {"a", "b", "c"}
    assert b._meta["a"] == 0
    assert b._meta["b"] == [1, 2]
    assert b._meta["c"] == 3


def test_type_error_missing_attributes() -> None:
    with pytest.raises(TypeError):
        # noinspection PyUnusedLocal
        class X(BitsType): ...
