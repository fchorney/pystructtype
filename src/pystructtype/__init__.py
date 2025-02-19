from pystructtype.bitstype import BitsType, bits
from pystructtype.structdataclass import StructDataclass, struct_dataclass
from pystructtype.structtypes import (
    TypeInfo,
    TypeMeta,
    char_t,
    double_t,
    float_t,
    int8_t,
    int16_t,
    int32_t,
    int64_t,
    uint8_t,
    uint16_t,
    uint32_t,
    uint64_t,
)

__all__ = [
    "BitsType",
    "StructDataclass",
    "TypeInfo",
    "TypeMeta",
    "bits",
    "char_t",
    "double_t",
    "float_t",
    "int8_t",
    "int16_t",
    "int32_t",
    "int64_t",
    "struct_dataclass",
    "uint8_t",
    "uint16_t",
    "uint32_t",
    "uint64_t",
]

# Note: This is how class decorators essentially work
#
# @foo
# class gotem(): ...
#
# is equal to: foo(gotem)
#
# @foo()
# class gotem(): ...
#
# is equal to: foo()(gotem)
#
# @foo(bar=2)
# class gotem(): ...
#
# is equal to: foo(bar=2)(gotem)
