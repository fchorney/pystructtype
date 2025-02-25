from typing import Annotated

import pytest

from pystructtype import (
    StructDataclass,
    TypeMeta,
    char_t,
    double_t,
    float_t,
    int8_t,
    int16_t,
    int32_t,
    int64_t,
    string_t,
    struct_dataclass,
    uint8_t,
    uint16_t,
    uint32_t,
    uint64_t,
)
from pystructtype.structtypes import TypeInfo, TypeIterator, iterate_types, type_from_annotation


def test_char_t():
    @struct_dataclass
    class MyStruct(StructDataclass):
        foo: char_t

    data = [ord(b"A")]
    s = MyStruct()
    s.decode(data)

    assert s.foo == b"A"

    e = s.encode()
    assert s._to_list(e) == data


def test_string_t():
    @struct_dataclass
    class MyStruct(StructDataclass):
        foo: string_t
        bar: Annotated[string_t, TypeMeta[bytes](chunk_size=3)]

    data = MyStruct._to_list(b"ABCD")
    s = MyStruct()
    s.decode(data)

    assert s.foo == b"A"
    assert s.bar == b"BCD"

    e = s.encode()
    assert s._to_list(e) == data


def test_unsigned_int():
    @struct_dataclass
    class MyStruct(StructDataclass):
        foo8: uint8_t
        foo16: uint16_t
        foo32: uint32_t
        foo64: uint64_t

    data = [254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254]
    s = MyStruct()
    s.decode(data)

    assert s.foo8 == 254
    assert s.foo16 == 65_278
    assert s.foo32 == 4_278_124_286
    assert s.foo64 == 18_374_403_900_871_474_942

    e = s.encode()
    assert s._to_list(e) == data


def test_signed_int():
    @struct_dataclass
    class MyStruct(StructDataclass):
        foo8: int8_t
        foo16: int16_t
        foo32: int32_t
        foo64: int64_t

    data = [254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254]
    s = MyStruct()
    s.decode(data)

    assert s.foo8 == -2
    assert s.foo16 == -258
    assert s.foo32 == -16_843_010
    assert s.foo64 == -72_340_172_838_076_674

    e = s.encode()
    assert s._to_list(e) == data


def test_floating_points():
    @struct_dataclass
    class MyStruct(StructDataclass):
        foo: float_t
        bar: double_t

    data = [68, 154, 82, 43, 65, 157, 111, 52, 87, 243, 91, 168]
    s = MyStruct()
    s.decode(data)

    assert s.foo == 1234.5677490234375
    assert s.bar == 123456789.987654321

    e = s.encode()
    assert s._to_list(e) == data


def test_basic_type_lists():
    @struct_dataclass
    class MyStruct(StructDataclass):
        int_type: Annotated[list[uint8_t], TypeMeta[int](size=2)]
        float_type: Annotated[list[float_t], TypeMeta[float](size=2)]
        char_type: Annotated[list[char_t], TypeMeta[bytes](size=2)]
        string_type: Annotated[list[string_t], TypeMeta[bytes](size=2, chunk_size=2)]

    int_data = [1, 2]
    float_data = [68, 154, 82, 43, 67, 153, 81, 42]
    char_data = MyStruct._to_list(b"AB")
    string_data = MyStruct._to_list(b"ABCD")

    data = int_data + float_data + char_data + string_data
    s = MyStruct()
    s.decode(data)

    assert s.int_type == [1, 2]
    assert s.float_type == [1234.5677490234375, 306.63409423828125]
    assert s.char_type == [b"A", b"B"]
    assert s.string_type == [b"AB", b"CD"]


class TestTypeFromAnnotation:
    def test_un_annotated(self):
        assert type_from_annotation(str) is str

    def test_single_annotation(self):
        assert type_from_annotation(Annotated[int, TypeMeta()]) is int

    def test_nested_annotation(self):
        assert type_from_annotation(Annotated[Annotated[int, TypeInfo("b", 1)], TypeMeta()]) is int


def test_iterate_types():
    @struct_dataclass
    class MyStruct(StructDataclass):
        foo: Annotated[list[uint8_t], TypeMeta[int](size=2)]

    results = [
        TypeIterator(
            key="foo",
            base_type=int,
            type_info=TypeInfo(format="B", byte_size=1),
            type_meta=TypeMeta(size=2),
            is_list=True,
            is_pystructtype=True,
        )
    ]
    assert list(iterate_types(MyStruct)) == results


def test_typemeta_eq_failure():
    with pytest.raises(TypeError):
        assert TypeMeta() == 2
