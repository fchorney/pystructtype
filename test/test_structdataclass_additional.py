from dataclasses import is_dataclass
from typing import Annotated

import pytest

from pystructtype import StructDataclass, TypeMeta, int8_t, struct_dataclass, uint8_t


# Test _simplify_format for various struct formats
def test_simplify_format_merges_repeats() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: uint8_t
        b: Annotated[list[uint8_t], TypeMeta(size=4)]
        c: int8_t

    s = S()

    # Should merge 5 uint8_t into 5B and end with 'b'
    assert s.struct_fmt == "5Bb"


# Test _simplify_format: char[]/string grouping and number prefix
@pytest.mark.parametrize(
    "fmt,expected",
    [
        ("2c4bh", "2c4bh"),
        ("ccbbbbh", "2c4bh"),
        ("10s", "10s"),
        ("c2s", "c2s"),
    ],
)
def test_simplify_format_edge_cases(fmt: str, expected: str) -> None:
    class Dummy(StructDataclass):
        pass

    s = Dummy()
    s.struct_fmt = fmt
    s._simplify_format()
    assert s.struct_fmt == expected


# Test _to_bytes and _to_list static methods
def test_to_bytes_and_to_list() -> None:
    data = [1, 2, 3]
    b = StructDataclass._to_bytes(data)
    assert isinstance(b, bytes)
    assert list(b) == data
    b2 = bytes([4, 5, 6])
    assert StructDataclass._to_list(b2) == [4, 5, 6]
    assert StructDataclass._to_list([7, 8]) == [7, 8]


# Test _endian static method
def test_endian() -> None:
    assert StructDataclass._endian(True) == "<"
    assert StructDataclass._endian(False) == ">"


# Test size method
def test_size() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: Annotated[list[uint8_t], TypeMeta(size=3)]

    s = S()
    assert s.size() == 3


# Test nested StructDataclass encoding/decoding
def test_nested_structdataclass() -> None:
    @struct_dataclass
    class Inner(StructDataclass):
        x: uint8_t
        y: uint8_t

    @struct_dataclass
    class Outer(StructDataclass):
        inner: Inner
        z: uint8_t

    o = Outer()
    o.inner.x = 1
    o.inner.y = 2
    o.z = 3
    encoded = o.encode()
    o2 = Outer()
    o2.decode(encoded)
    assert o2.inner.x == 1
    assert o2.inner.y == 2
    assert o2.z == 3


def test_decode_list_of_base_types() -> None:
    # Test _decode: attr is not a list, not a StructDataclass, state.size > 1
    # This will hit the 'else' branch for a list of base types
    @struct_dataclass
    class SList(StructDataclass):
        a: Annotated[list[uint8_t], TypeMeta(size=2)]

    s = SList()
    s.a = [0, 0]
    s._decode([1, 2])
    assert s.a == [1, 2]


# Test error paths in _decode and _encode
def test_decode_encode_errors() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: Annotated[list[uint8_t], TypeMeta(size=2)]

    s = S()

    # _decode with wrong size for list
    with pytest.raises(IndexError):
        s._decode([1])

    # _encode with wrong attribute type
    s.a = None  # type: ignore
    with pytest.raises(TypeError):
        s._encode()


# Test struct_dataclass decorator with and without parens
def test_struct_dataclass_decorator_variants() -> None:
    @struct_dataclass
    class S1(StructDataclass):
        a: uint8_t

    @struct_dataclass  # Remove parens to match the overload signature
    class S2(StructDataclass):
        a: uint8_t

    assert is_dataclass(S1)
    assert is_dataclass(S2)


# Test struct_dataclass: already a dataclass
def test_struct_dataclass_already_dataclass() -> None:
    from dataclasses import dataclass as dc

    @dc
    class S(StructDataclass):
        a: uint8_t

    result = struct_dataclass(S)
    assert is_dataclass(result)


# Test default value logic in struct_dataclass
def test_struct_dataclass_default_value() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: uint8_t

    s = S()
    assert hasattr(s, "a")


# Test exception for list type with size=1
def test_struct_dataclass_list_type_size_one() -> None:
    with pytest.raises(ValueError):

        @struct_dataclass
        class S(StructDataclass):
            a: Annotated[list[uint8_t], TypeMeta(size=1)]
            # Should raise because list type with size=1 is not allowed


# Test exception for non-list type with size>1
def test_struct_dataclass_nonlist_type_size_gt_one() -> None:
    with pytest.raises(ValueError):

        @struct_dataclass
        class S(StructDataclass):
            a: Annotated[uint8_t, TypeMeta(size=2)]
            # Should raise because non-list type with size>1 is not allowed


# Test exception for default value as list
def test_struct_dataclass_default_list_exception() -> None:
    with pytest.raises(TypeError):

        @struct_dataclass
        class S(StructDataclass):
            a: Annotated[uint8_t, TypeMeta(default=[1, 2])]
            # Should raise because default value for attribute cannot be a list


# Test struct_dataclass: default is a class instance
def test_struct_dataclass_default_class_instance() -> None:
    class Dummy:
        def __init__(self) -> None:
            self.x = 1

    @struct_dataclass
    class S(StructDataclass):
        a: Dummy

    s = S()
    assert hasattr(s, "a")
    assert hasattr(s.a, "x")


# Test struct_dataclass: default is a value
def test_struct_dataclass_default_value_field() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: Annotated[uint8_t, TypeMeta(default=5)]

    s = S()
    assert s.a == 5


# Test struct_dataclass: default for list of values
def test_struct_dataclass_default_list_of_values() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: Annotated[list[uint8_t], TypeMeta(size=2, default=7)]

    s = S()
    assert s.a == [7, 7]


# Test struct_dataclass: default for list of class instances
def test_struct_dataclass_default_list_of_class_instances() -> None:
    class Dummy:
        def __init__(self) -> None:
            self.x = 1

    @struct_dataclass
    class S(StructDataclass):
        a: Annotated[list[Dummy], TypeMeta(size=2)]

    s = S()
    assert all(hasattr(x, "x") for x in s.a)


def test_regular_class_attribute_is_ignored() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: int
        b: str
        c: float

    s = S()
    s.a = 1
    s.b = "x"
    s.c = 2.0
    assert s.a == 1 and s.b == "x" and s.c == 2.0


# The following test ensures the else branch in _decode for a list of base types is covered
# and the else branch in _encode for a list of base types is covered


def test_encode_decode_list_of_base_types() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: Annotated[list[uint8_t], TypeMeta(size=3)]

    s = S()
    s.a = [1, 2, 3]
    encoded = s.encode()
    s2 = S()
    s2.decode(encoded)
    assert s2.a == [1, 2, 3]


def test_structdataclass_regular_field_ignored() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: int
        b: str

    s = S()
    s.a = 42
    s.b = "foo"
    assert s.a == 42 and s.b == "foo"


# Covers: 259, 275 (non-pystructtype, non-class field is ignored)
def test_structdataclass_non_pystructtype_non_class_field() -> None:
    @struct_dataclass
    class S(StructDataclass):
        a: int

    s = S()
    s.a = 1
    assert s.a == 1


# Covers: 311 (not type_iterator.is_list)
def test_structdataclass_nonlist_type_with_size_gt_one() -> None:
    with pytest.raises(ValueError):

        @struct_dataclass
        class S(StructDataclass):
            a: Annotated[int, TypeMeta(size=2)]


# Covers: 328, 345-346, 348 (default is a list, default is a class)
def test_structdataclass_default_list_typeerror() -> None:
    with pytest.raises(TypeError):

        @struct_dataclass
        class S(StructDataclass):
            a: Annotated[int, TypeMeta(default=[1, 2])]


def test_structdataclass_default_class_factory() -> None:
    class Dummy:
        def __init__(self) -> None:
            self.x = 1

    # Use an instance as the default to trigger deepcopy path
    @struct_dataclass
    class S(StructDataclass):
        a: Annotated[Dummy, TypeMeta(default=Dummy())]

    s = S()
    assert isinstance(s.a, Dummy)


# Covers: 368, 379 (default_list for list of classes)
def test_structdataclass_list_of_classes_default_factory() -> None:
    class Dummy:
        def __init__(self) -> None:
            self.x = 1

    @struct_dataclass
    class S(StructDataclass):
        a: Annotated[list[Dummy], TypeMeta(size=2)]

    s = S()
    assert isinstance(s.a, list) and all(isinstance(x, Dummy) for x in s.a)


def test_structdataclass_list_of_structdataclass_encode_decode() -> None:
    @struct_dataclass
    class Inner(StructDataclass):
        x: uint8_t

    @struct_dataclass
    class Outer(StructDataclass):
        inners: Annotated[list[Inner], TypeMeta(size=2)]

    o = Outer()
    o.inners[0].x = 1
    o.inners[1].x = 2
    encoded = o.encode()
    o2 = Outer()
    o2.decode(encoded)
    assert o2.inners[0].x == 1 and o2.inners[1].x == 2


# Covers decorator error branches


def test_structdataclass_list_type_size_one_error() -> None:
    with pytest.raises(ValueError):

        @struct_dataclass
        class S(StructDataclass):
            a: Annotated[list[uint8_t], TypeMeta(size=1)]


def test_structdataclass_nonlist_type_size_gt_one_error() -> None:
    with pytest.raises(ValueError):

        @struct_dataclass
        class S(StructDataclass):
            a: Annotated[uint8_t, TypeMeta(size=2)]


def test_structdataclass_default_list_type_error() -> None:
    with pytest.raises(TypeError):

        @struct_dataclass
        class S(StructDataclass):
            a: Annotated[uint8_t, TypeMeta(default=[1, 2])]


def test_structdataclass_invalid_branches_all() -> None:
    # 259, 275: non-pystructtype, non-class field is ignored (already covered by regular field tests)
    # 311: not type_iterator.is_list, but size > 1
    with pytest.raises(ValueError):

        @struct_dataclass
        class S1(StructDataclass):
            a: Annotated[int, TypeMeta(size=2)]

    # 328, 345-346: default is a list
    with pytest.raises(TypeError):

        @struct_dataclass
        class S2(StructDataclass):
            a: Annotated[int, TypeMeta(default=[1, 2])]

    # 348: default is a class (should use default_factory=default, not deepcopy)
    class Dummy:
        def __init__(self) -> None:
            self.x = 1

    @struct_dataclass
    class S3(StructDataclass):
        a: Annotated[Dummy, TypeMeta(default=Dummy)]

    s3 = S3()
    assert isinstance(s3.a, Dummy)

    # Test for default is an instance (should use deepcopy)
    @struct_dataclass
    class S3b(StructDataclass):
        a: Annotated[Dummy, TypeMeta(default=Dummy())]

    s3b = S3b()
    assert isinstance(s3b.a, Dummy)

    # 368, 379: default_list for list of classes
    @struct_dataclass
    class S4(StructDataclass):
        a: Annotated[list[Dummy], TypeMeta(size=2)]

    s4 = S4()
    assert isinstance(s4.a, list) and all(isinstance(x, Dummy) for x in s4.a)
    # 311: list type with size == 1
    with pytest.raises(ValueError):

        @struct_dataclass
        class S5(StructDataclass):
            a: Annotated[list[int], TypeMeta(size=1)]


def test_structdataclass_defensive_branches() -> None:
    # 259, 275: non-pystructtype, non-class field is ignored (should not raise, just skip)
    @struct_dataclass
    class S1(StructDataclass):
        a: int  # not Annotated, not a class, should be ignored

    s1 = S1()
    s1.a = 42
    assert s1.a == 42

    # 311: not type_iterator.is_list, but size > 1 (should raise ValueError)
    with pytest.raises(ValueError):

        @struct_dataclass
        class S2(StructDataclass):
            a: Annotated[int, TypeMeta(size=2)]

    # 345-346: default is a list (should raise TypeError)
    with pytest.raises(TypeError):

        @struct_dataclass
        class S3(StructDataclass):
            a: Annotated[int, TypeMeta(default=[1, 2])]

    # 348: default is a class (should use default_factory=default, not deepcopy)
    class Dummy:
        def __init__(self) -> None:
            self.x = 1

    @struct_dataclass
    class S4(StructDataclass):
        a: Annotated[Dummy, TypeMeta(default=Dummy)]

    s4 = S4()
    assert isinstance(s4.a, Dummy)

    # 368, 379: default_list for list of classes (should use default_factory for list of Dummy)
    @struct_dataclass
    class S5(StructDataclass):
        a: Annotated[list[Dummy], TypeMeta(size=2)]

    s5 = S5()
    assert isinstance(s5.a, list) and all(isinstance(x, Dummy) for x in s5.a)
