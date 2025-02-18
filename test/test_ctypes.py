from pystructtype import struct_dataclass, StructDataclass, uint8_t, TypeMeta, bits, BitsType, int16_t, char_t, \
    double_t, float_t, uint16_t
from .examples import SMXConfigType, TEST_CONFIG_DATA  # type: ignore
from typing import Annotated

def test_examples():
    @struct_dataclass
    class MyStruct(StructDataclass):
        myNum: int16_t
        myLetter: char_t

    s = MyStruct()
    s.decode([4, 2, 65])
    s.decode([4, 2, 65], little_endian=True)

    @struct_dataclass
    class MyStruct2(StructDataclass):
        myFloat: float_t
        myDouble: double_t

    s2 = MyStruct2()
    s2.decode([1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 7, 8])
    s2.decode([1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 7, 8])

    @struct_dataclass
    class MyStruct3(StructDataclass):
        myInts: Annotated[list[uint8_t], TypeMeta(size=4)]
        myBiggerInts: Annotated[list[uint16_t], TypeMeta(size=2)]

    s3 = MyStruct3()
    s3.decode([0, 64, 128, 255, 16, 0, 255, 255])

    @bits(uint8_t, {"lights_flag": 0, "platform_flag": 1})
    class FlagsType(BitsType): ...

    f = FlagsType()
    f.decode([3])


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
