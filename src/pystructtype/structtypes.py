import inspect
from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated, Any, TypeVar, get_args, get_origin, get_type_hints

from pystructtype import structdataclass

T = TypeVar("T", int, float, default=int)
"""Generic Data Type for StructDataclass Contents"""


@dataclass(frozen=True)
class TypeMeta[T]:
    """
    Class used to define Annotated Type Metadata for
    size and default values
    """

    size: int = 1
    default: T | None = None


@dataclass(frozen=True)
class TypeInfo:
    """
    Class used to define Annotated Type Metadata
    for format and byte size
    """

    format: str
    byte_size: int


# TODO: Support proper "c-string" types

# Fixed Size Types
char_t = Annotated[int, TypeInfo("c", 1)]
"""1 Byte char Type"""
int8_t = Annotated[int, TypeInfo("b", 1)]
"""1 Byte Signed int Type"""
uint8_t = Annotated[int, TypeInfo("B", 1)]
"""1 Byte Unsigned int Type"""
int16_t = Annotated[int, TypeInfo("h", 2)]
"""2 Byte Signed int Type"""
uint16_t = Annotated[int, TypeInfo("H", 2)]
"""2 Byte Unsigned int Type"""
int32_t = Annotated[int, TypeInfo("i", 4)]
"""4 Byte Signed int Type"""
uint32_t = Annotated[int, TypeInfo("I", 4)]
"""4 Byte Unsigned int Type"""
int64_t = Annotated[int, TypeInfo("q", 8)]
"""8 Byte Signed int Type"""
uint64_t = Annotated[int, TypeInfo("Q", 8)]
"""8 Byte Unsigned int Type"""

# TODO: Make a special Bool class to auto-convert from int to bool

# Named Types
float_t = Annotated[float, TypeInfo("f", 4)]
"""4 Byte float Type"""
double_t = Annotated[float, TypeInfo("d", 8)]
"""8 Byte double Type"""


@dataclass
class TypeIterator:
    """
    Contains all relevant type information for
    an object in a StructDataclass.

    Used as a container when iterating through StructDataclass attributes
    """

    key: str
    base_type: type
    type_info: TypeInfo | None
    type_meta: TypeMeta | None
    is_list: bool
    is_pystructtype: bool

    @property
    def size(self) -> int:
        """
        Return the size of the type. If this is not a list, this will default to
        1, else this will return the size defined in the `type_meta` object
        if it exists.

        :return: integer containing the size of the type
        """
        return getattr(self.type_meta, "size", 1)


def iterate_types(cls: type) -> Generator[TypeIterator]:
    """
    Iterate through the given StructDataclass attributes type hints and yield
    a TypeIterator for each one.

    :param cls: A StructDataclass class object (not an instantiated object)
    :return: Yield a TypeIterator object
    """
    for key, hint in get_type_hints(cls, include_extras=True).items():
        # Grab the base type from a possibly annotated type hint
        base_type = type_from_annotation(hint)

        # Determine if the type is a list
        # ex. list[bool] (yes) vs bool (no)
        is_list = issubclass(origin, list) if (origin := get_origin(base_type)) else False

        # Grab the first args value and look for any TypeMeta objects within
        type_args = get_args(hint)
        type_meta = next((x for x in type_args if isinstance(x, TypeMeta)), None)

        # type_args has the possibility of being nested within more tuples
        # drill down the type_args until we hit empty, then we know we're at the bottom
        # which is where type_info will exist
        if type_args and len(type_args) > 1:
            while args := get_args(type_args[0]):
                type_args = args

        # Find the TypeInfo object on the lowest rung of the type_args
        type_info = next((x for x in type_args if isinstance(x, TypeInfo)), None)

        # At this point we may have possibly drilled down into `type_args` to find the true base type
        if type_args:
            base_type = type_from_annotation(type_args[0])

        # Determine if we are a subclass of a pystructtype:
        # A pystructtype will be a type with a type_info object in the Annotation,
        # or a subtype of StructDataclass
        is_pystructtype = type_info is not None or (
            inspect.isclass(base_type) and issubclass(base_type, structdataclass.StructDataclass)
        )

        yield TypeIterator(key, base_type, type_info, type_meta, is_list, is_pystructtype)


def type_from_annotation(_type: type) -> type:
    """
    Find the base type from an Annotated type,
    or return it unchanged if not Annotated

    :param _type: Type to check
    :return: Base type if Annotated, or the original passed in type otherwise
    """
    # If we have an origin for the given type, and it's Annotated
    if (origin := get_origin(_type)) and origin is Annotated:
        # Keep running `get_args` on the first element of whatever
        # `get_args` returns, until we get nothing back
        arg = _type
        t: Any = _type
        while t := get_args(t):
            arg = t[0]

        # This will be the base type
        return arg
    # No origin, or the origin is not Annotated, just return the given type
    return _type
