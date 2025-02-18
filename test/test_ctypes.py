from typing import Annotated

from pystructtype import (
    BitsType,
    StructDataclass,
    TypeMeta,
    bits,
    struct_dataclass,
    uint8_t,
)

from .examples import TEST_CONFIG_DATA, SMXConfigType  # type: ignore


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
