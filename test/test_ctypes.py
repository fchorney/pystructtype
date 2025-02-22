from typing import Annotated

from pystructtype import BitsType, StructDataclass, TypeMeta, bits, string_t, struct_dataclass, uint8_t

from .examples import TEST_CONFIG_DATA, SMXConfigType  # type: ignore


def test_strings():
    @struct_dataclass
    class TestString(StructDataclass):
        boo: uint8_t
        foo: Annotated[string_t, TypeMeta[str](chunk_size=3)]
        far: Annotated[list[uint8_t], TypeMeta(size=2)]
        bar: Annotated[string_t, TypeMeta[str](chunk_size=5)]
        rob: uint8_t
        rar: Annotated[list[string_t], TypeMeta[str](size=2, chunk_size=2)]

    data = [0, 65, 66, 67, 1, 2, 65, 66, 67, 68, 69, 2, 65, 66, 67, 68]

    s = TestString()
    s.decode(data)

    assert s.foo == b"ABC"
    assert s.bar == b"ABCDE"
    assert s.boo == 0
    assert s.far == [1, 2]
    assert s.rob == 2
    assert s.rar == [b"AB", b"CD"]

    e = s.encode()
    assert s._to_list(e) == data


def test_smx_config():
    c = SMXConfigType()

    c.decode(TEST_CONFIG_DATA, little_endian=True)
    e = c.encode(little_endian=True)

    assert c._to_list(e) == TEST_CONFIG_DATA


def test_sd():
    @struct_dataclass
    class Test(StructDataclass):
        foo: Annotated[list[uint8_t], TypeMeta(size=2, default=4)]

    @struct_dataclass
    class Test2(StructDataclass):
        bar: Annotated[list[Test], TypeMeta(size=2)]
        baz: uint8_t
        zap: Annotated[list[Test], TypeMeta(size=2)]

    data2 = [1, 2, 3, 4, 5, 6, 7, 8, 9]

    c = Test2()

    c.decode(data2)
    e = c.encode()

    assert c._to_list(e) == data2


def test_bits():
    @bits(Annotated[list[uint8_t], TypeMeta(size=2)], {"a": 0, "b": 4, "c": 11, "d": 15})
    class BitsTest(BitsType): ...

    data = [0b1000_1000, 0b0001_0001]

    c = BitsTest()

    c.decode(data)

    e = c.encode()

    assert c._to_list(e) == data
