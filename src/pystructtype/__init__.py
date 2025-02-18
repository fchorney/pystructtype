import inspect
import itertools
import re
import struct
from collections.abc import Callable, Generator
from copy import deepcopy
from dataclasses import dataclass, field, is_dataclass
from typing import (
    Annotated,
    Any,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)


def list_chunks(_list: list, n: int) -> Generator[list]:
    """
    Yield successive n-sized chunks from a list.
    :param _list: List to chunk out
    :param n: Size of chunks
    :return: Generator of n-sized chunks of _list
    """
    yield from (_list[i : i + n] for i in range(0, len(_list), n))


def type_from_annotation(_type: type) -> type:
    """
    Find the base type from an Annotated type, or return it unchanged if
    not Annotated
    :param _type: Type to check
    :return: Annotated base type or the given type if not Annotated
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


T = TypeVar("T", int, float, default=int)


@dataclass(frozen=True)
class TypeMeta[T]:
    size: int = 1
    default: T | None = None


@dataclass(frozen=True)
class TypeInfo:
    format: str
    byte_size: int


# Fixed Size Types
int8_t = Annotated[int, TypeInfo("b", 1)]
uint8_t = Annotated[int, TypeInfo("B", 1)]
int16_t = Annotated[int, TypeInfo("h", 2)]
uint16_t = Annotated[int, TypeInfo("H", 2)]
int32_t = Annotated[int, TypeInfo("i", 4)]
uint32_t = Annotated[int, TypeInfo("I", 4)]
int64_t = Annotated[int, TypeInfo("q", 8)]
uint64_t = Annotated[int, TypeInfo("Q", 8)]

# Named Types
bool_t = Annotated[bool, TypeInfo("?", 1)]
float_t = Annotated[float, TypeInfo("f", 4)]
double_t = Annotated[float, TypeInfo("d", 8)]


@dataclass
class TypeIterator:
    key: str
    base_type: type
    type_info: TypeInfo | None
    type_meta: TypeMeta | None
    is_list: bool
    is_pystructtype: bool

    @property
    def size(self):
        return getattr(self.type_meta, "size", 1)


def iterate_types(cls) -> Generator[TypeIterator]:
    for key, hint in get_type_hints(cls, include_extras=True).items():
        # Grab the base type from a possibly annotated type hint
        base_type = type_from_annotation(hint)

        # Determine if the type is a list
        # ex. list[bool] (yes) vs bool (no)
        is_list = issubclass(origin, list) if (origin := get_origin(base_type)) else False

        # Grab the type hints top args and look for any TypeMeta objects
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

        # Determine if we are a subclass of a pystructtype
        # If we have a type_info object in the Annotation, or we're actually a subtype of StructDataclass
        is_pystructtype = type_info is not None or (
            inspect.isclass(base_type) and issubclass(base_type, StructDataclass)
        )

        yield TypeIterator(key, base_type, type_info, type_meta, is_list, is_pystructtype)


@dataclass
class StructState:
    name: str
    struct_fmt: str
    size: int


class StructDataclass:
    def __post_init__(self):
        self._state: list[StructState] = []
        # Grab Struct Format
        self.struct_fmt = ""
        for type_iterator in iterate_types(self.__class__):
            if type_iterator.type_info:
                self._state.append(
                    StructState(
                        type_iterator.key,
                        type_iterator.type_info.format,
                        type_iterator.size,
                    )
                )
                self.struct_fmt += (
                    f"{type_iterator.size if type_iterator.size > 1 else ''}{type_iterator.type_info.format}"
                )
            elif inspect.isclass(type_iterator.base_type) and issubclass(type_iterator.base_type, StructDataclass):
                attr = getattr(self, type_iterator.key)
                if type_iterator.is_list:
                    fmt = attr[0].struct_fmt
                else:
                    fmt = attr.struct_fmt
                self._state.append(StructState(type_iterator.key, fmt, type_iterator.size))
                self.struct_fmt += fmt * type_iterator.size
            else:
                # We have no TypeInfo object, and we're not a StructDataclass
                # This means we're a regularly defined class variable, and we
                # Don't have to do anything about this.
                pass
        self._simplify_format()
        self._byte_length = struct.calcsize("=" + self.struct_fmt)
        print(f"{self.__class__.__name__}: {self._byte_length} : {self.struct_fmt}")

    def _simplify_format(self) -> None:
        # First expand the format
        expanded_format = ""
        items = re.findall(r"([a-zA-Z]|\d+)", self.struct_fmt)
        items_len = len(items)
        idx = 0
        while idx < items_len:
            if "0" <= (item := items[idx]) <= "9":
                idx += 1
                expanded_format += items[idx] * int(item)
            else:
                expanded_format += item
            idx += 1

        simplified_format = ""
        for group in (x[0] for x in re.findall(r"(([a-zA-Z])\2*)", expanded_format)):
            group_len = len(group)
            simplified_format += f"{group_len if group_len > 1 else ''}{group[0]}"

        self.struct_fmt = simplified_format

    def size(self) -> int:
        return sum(state.size for state in self._state)

    @staticmethod
    def _endian(little_endian: bool) -> str:
        return "<" if little_endian else ">"

    @staticmethod
    def _to_bytes(data: list[int] | bytes) -> bytes:
        if isinstance(data, bytes):
            return data
        return bytes(data)

    @staticmethod
    def _to_list(data: list[int] | bytes) -> list[int]:
        if isinstance(data, bytes):
            return list(data)
        return data

    def _decode(self, data: list[int]) -> None:
        idx = 0

        for state in self._state:
            attr = getattr(self, state.name)

            if isinstance(attr, list) and isinstance(attr[0], StructDataclass):
                list_idx = 0
                sub_struct_byte_length = attr[0].size()
                while list_idx < state.size:
                    instance: StructDataclass = attr[list_idx]
                    instance._decode(data[idx : idx + sub_struct_byte_length])
                    list_idx += 1
                    idx += sub_struct_byte_length
            elif isinstance(attr, StructDataclass):
                if state.size != 1:
                    raise Exception("This should be a size of one, dingus")

                sub_struct_byte_length = attr.size()
                attr._decode(data[idx : idx + sub_struct_byte_length])
                idx += sub_struct_byte_length
            elif state.size == 1:
                setattr(self, state.name, data[idx])
                idx += 1
            else:
                list_idx = 0
                while list_idx < state.size:
                    getattr(self, state.name)[list_idx] = data[idx]
                    list_idx += 1
                    idx += 1

    def decode(self, data: list[int] | bytes, little_endian=False) -> None:
        data = self._to_bytes(data)

        # Decode
        self._decode(list(struct.unpack(self._endian(little_endian) + self.struct_fmt, data)))

    def _encode(self) -> list[int]:
        result: list[int] = []

        for state in self._state:
            attr = getattr(self, state.name)

            if isinstance(attr, list) and isinstance(attr[0], StructDataclass):
                item: StructDataclass
                for item in attr:
                    result.extend(item._encode())
            elif isinstance(attr, StructDataclass):
                if state.size != 1:
                    raise Exception("This should be a size of one, dingus")
                result.extend(attr._encode())
            elif state.size == 1:
                result.append(getattr(self, state.name))
            else:
                result.extend(getattr(self, state.name))
        return result

    def encode(self, little_endian=False) -> bytes:
        result = self._encode()
        return struct.pack(self._endian(little_endian) + self.struct_fmt, *result)


@overload
def struct_dataclass(_cls: type[StructDataclass]) -> type[StructDataclass]: ...


@overload
def struct_dataclass(_cls: None) -> Callable[[type[StructDataclass]], type[StructDataclass]]: ...


def struct_dataclass(
    _cls: type[StructDataclass] | None = None,
) -> Callable[[type[StructDataclass]], type[StructDataclass]] | type[StructDataclass]:
    def inner(_cls: type[StructDataclass]) -> type[StructDataclass]:
        new_cls = _cls

        # new_cls should not already be a dataclass
        if is_dataclass(new_cls):
            return cast(type[StructDataclass], new_cls)

        # Make sure any fields without a default have one
        for type_iterator in iterate_types(new_cls):
            if not type_iterator.is_pystructtype:
                continue

            if not type_iterator.type_meta or type_iterator.type_meta.size == 1:
                if type_iterator.is_list:
                    raise Exception("You said this should be size 1, so this shouldn't be a list")

                # Set a default if it does not yet exist
                if not getattr(new_cls, type_iterator.key, None):
                    default: type | int | float = type_iterator.base_type
                    if type_iterator.type_meta and type_iterator.type_meta.default:
                        default = type_iterator.type_meta.default
                        if isinstance(default, list):
                            raise Exception("A default for a size 1 should not be a list")

                    # Create a new instance of the class
                    if inspect.isclass(default):
                        default = field(default_factory=lambda d=default: d())  # type: ignore
                    else:
                        default = field(default_factory=lambda d=default: deepcopy(d))  # type: ignore

                    setattr(new_cls, type_iterator.key, default)
            else:
                # This assumes we want multiple items of base_type, so make sure the given base_type is
                # properly set to be a list as well
                if not type_iterator.is_list:
                    raise Exception("You want a list, so make it a list you dummy")

                # We have a meta type and the size is > 1 so make the default a field
                default = type_iterator.base_type
                if type_iterator.type_meta and type_iterator.type_meta.default:
                    default = type_iterator.type_meta.default

                default_list = []
                if isinstance(default, list):
                    pass
                else:
                    # Create a new instance of the class
                    if inspect.isclass(default):
                        default_list = field(
                            default_factory=lambda d=default, s=type_iterator.type_meta.size: [  # type: ignore
                                d() for _ in range(s)
                            ]
                        )
                    else:
                        default_list = field(
                            default_factory=lambda d=default, s=type_iterator.type_meta.size: [  # type: ignore
                                deepcopy(d) for _ in range(s)
                            ]
                        )

                setattr(new_cls, type_iterator.key, default_list)
        return cast(type[StructDataclass], dataclass(new_cls))

    if _cls is None:
        return inner
    return inner(_cls)


def int_to_bool_list(data: int | list[int], byte_length: int) -> list[bool]:
    """
    Converts integer or a list of integers into a list of bools representing the bits

    ex. ord("A") = [False, True, False, False, False, False, False, True]

    ex. [ord("A"), ord("B")] = [False, True, False, False, False, False, False, True,
    False, True, False, False, False, False, True, False]

    :param data: Integer(s) to be converted
    :param byte_length: Number of bytes to extract from integer(s)
    :return: List of bools representing each bit in the data
    """
    # Convert a single int into a list, so we can assume we're always working with a list here
    data = [data] if isinstance(data, int) else data

    # The amount of bits we end up with will be the number of bytes we expect in the int times 8 (8 bits in a byte)
    # For example uint8_t would have 1 byte, but uint16_t would have 2 bytes
    byte_size = (byte_length * 8) // len(data)

    bit_strs = []
    for val in data:
        # Convert the int(s) in to a string of bits (add 2 to account for the `0b` prefix)
        tmp_str = format(val, f"#0{byte_size + 2}b")
        # Cut off the `0b` prefix of the bit string, and reverse it
        bit_strs.append(tmp_str.removeprefix("0b")[::-1])
    # Convert the bit_str to a list of ints
    bit_list = map(int, "".join(bit_strs[::-1]))
    # Convert the bit list to bools and return
    return list(map(bool, bit_list))


class BitsType(StructDataclass):
    _raw: Any
    _meta: dict
    _meta_tuple: tuple

    def __post_init__(self):
        super().__post_init__()

        self._meta = {k: v for k, v in zip(*self._meta_tuple, strict=False)}

    def _decode(self, data: list[int]) -> None:
        # First call the super function to put the values in to _raw
        super()._decode(data)

        # Combine all data in _raw as binary and convert to bools
        bin_data = int_to_bool_list(self._raw, self._byte_length)

        for k, v in self._meta.items():
            if isinstance(v, list):
                steps = []
                for idx in v:
                    steps.append(bin_data[idx])
                setattr(self, k, steps)
            else:
                setattr(self, k, bin_data[v])

    def _encode(self) -> list[int]:
        bin_data = list(itertools.repeat(False, self._byte_length * 8))
        for k, v in self._meta.items():
            if isinstance(v, list):
                steps = getattr(self, k)
                for idx, bit_idx in enumerate(v):
                    bin_data[bit_idx] = steps[idx]
            else:
                bin_data[v] = getattr(self, k)

        if isinstance(self._raw, list):
            self._raw = [
                sum(v << i for i, v in enumerate(chunk))
                for chunk in list_chunks(bin_data, (self._byte_length // len(self._raw)) * 8)
            ][::-1]
        else:
            self._raw = sum(v << i for i, v in enumerate(bin_data))

        # Run the super function to return the data in self._raw()
        return super()._encode()


def bits(_type: Any, definition: dict[str, int | list[int]]) -> Callable[[type[BitsType]], type[StructDataclass]]:
    def inner(_cls: type[BitsType]) -> type[StructDataclass]:
        # Create class attributes based on the definition
        # TODO: Maybe a sanity check to make sure the definition is the right format, and no overlapping bits, etc

        new_cls = _cls

        new_cls.__annotations__["_raw"] = _type

        new_cls._meta = field(default_factory=dict)
        new_cls.__annotations__["_meta"] = dict[str, int]

        # Convert the definition to a named tuple, so it's Immutable
        meta_tuple = (tuple(definition.keys()), tuple(definition.values()))
        new_cls._meta_tuple = field(default_factory=lambda d=meta_tuple: d)  # type: ignore
        new_cls.__annotations__["_meta_tuple"] = tuple

        # TODO: Support int, or list of ints as defaults
        # TODO: Support dict, and dict of lists, or list of dicts, etc for definition
        # TODO: ex. definition = {"a": {"b": 0, "c": [1, 2, 3]}, "d": [4, 5, 6], "e": {"f": 7}}
        # TODO: Can't decide if the line above this is a good idea or not
        for key, value in definition.items():
            if isinstance(value, list):
                setattr(
                    new_cls,
                    key,
                    field(default_factory=lambda v=len(value): [False for _ in range(v)]),  # type: ignore # noqa: B008
                )
                new_cls.__annotations__[key] = list[bool]
            else:
                setattr(new_cls, key, False)
                new_cls.__annotations__[key] = bool

        return struct_dataclass(new_cls)

    return inner


# XXX: This is how class decorators essentially work
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
