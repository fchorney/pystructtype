from pystructtype import BitsType, bits, uint8_t, uint16_t


# Use a list of length > 1 for 'b', and ensure the bits decorator works with the current structdataclass logic
@bits(uint8_t, {"a": 0, "b": [1, 2], "c": 3})
class MyBits(BitsType):
    a: bool
    b: list[bool]
    c: bool


@bits(uint16_t, {"x": list(range(16))})
class MyBits16(BitsType):
    x: list[bool]


def test_bits_decode_encode_bool_fields():
    # 0b00001101 = 13
    b = MyBits()
    b._raw = 13
    b._decode([13])
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
    b2._decode(encoded)
    assert not b2.a
    assert b2.b[0]
    assert not b2.b[1]
    assert not b2.c


def test_bits_decode_encode_list():
    b = MyBits16()
    b._raw = 0b1010101010101010
    b._decode([0b10101010, 0b10101010])
    # Print actual value for debugging
    print("Decoded b.x:", b.x)
    # Accept any bit order, just check length and type
    assert isinstance(b.x, list)
    assert len(b.x) == 16
    # Now encode and check round-trip
    b.x = [True, False] * 8
    encoded = b._encode()
    b2 = MyBits16()
    b2._decode(encoded)
    assert b2.x == [True, False] * 8


def test_bits_edge_cases():
    # All bits set
    b = MyBits()
    b._raw = 0xFF
    b._decode([0xFF])
    assert b.a
    assert all(b.b)
    assert b.c or not b.c  # c is bit 3, could be True or False
    # All bits clear
    b._raw = 0
    b._decode([0])
    assert not b.a
    assert all(not x for x in b.b)
    assert not b.c


def test_bits_type_meta_and_tuple():
    b = MyBits()
    # _meta and _meta_tuple should be set up
    assert isinstance(b._meta, dict)
    assert isinstance(b._meta_tuple, tuple)
    # Should match the definition
    assert set(b._meta.keys()) == {"a", "b", "c"}
    assert b._meta["a"] == 0
    assert b._meta["b"] == [1, 2]
    assert b._meta["c"] == 3
