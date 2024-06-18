import inspect
import itertools
import re
import struct
from copy import deepcopy  # noqa
from dataclasses import dataclass, field, is_dataclass
from typing import (
    Annotated,
    Any,
    Callable,
    Generator,
    Type,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)


def list_chunks(_list: list, chunk_size: int) -> Generator[list, None, None]:
    for i in range(0, len(_list), chunk_size):
        yield _list[i : i + chunk_size]


def type_from_annotation(_type: type):
    if (origin := get_origin(_type)) and origin is Annotated:
        arg = None
        t: Any = _type
        while t := get_args(t):
            arg = t[0]
        return arg
    return _type


@dataclass
class TypeMeta:
    size: int = 1
    default: Any | None = None


@dataclass
class TypeInfo:
    format: str
    byte_size: int


# Fixed Size Types
# int8_t = Annotated[int, "b"]  # 1 Byte
uint8_t = Annotated[int, TypeInfo("B", 1)]
# int16_t = Annotated[int, "h"]  # 2 Bytes
uint16_t = Annotated[int, TypeInfo("H", 2)]
# int32_t = Annotated[int, "i"]  # 4 Bytes
# uint32_t = Annotated[int, "I"]  # 4 Bytes
# int64_t = Annotated[int, "q"]  # 8 Bytes
# uint64_t = Annotated[int, "Q"]  # 8 Bytes

# Named Types
# char: TypeAlias = Annotated[int, "b"]  # 1 Byte
# unsigned_char: TypeAlias = Annotated[int, "B"]  # 1 Byte
# # bool: TypeAlias = Annotated[int, '?']  # 1 Byte
# short: TypeAlias = Annotated[int, "h"]  # 2 Bytes
# unsigned_short: TypeAlias = Annotated[int, "H"]  # 2 Bytes
# # int: TypeAlias = Annotated[int, 'i']  # 4 Bytes
# unsigned_int: TypeAlias = Annotated[int, "I"]  # 4 Bytes
# long: TypeAlias = Annotated[int, "l"]  # 4 Bytes
# unsigned_long: TypeAlias = Annotated[int, "L"]  # 4 Bytes
# long_long: TypeAlias = Annotated[int, "q"]  # 8 Bytes
# unsigned_long_long: TypeAlias = Annotated[int, "Q"]  # 8 Bytes
# # float: TypeAlias = Annotated[float, 'f']  # 4 Bytes
# double: TypeAlias = Annotated[float, "d"]  # 8 Bytes


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


# TODO: Clean this up
def iterate_types(cls) -> Generator[TypeIterator, None, None]:
    is_list = False
    for key, hint in get_type_hints(cls, include_extras=True).items():
        if inspect.isclass(hint) and issubclass(hint, StructDataclass):
            type_args = get_args(hint)
            is_list = False
        elif isinstance(type_args := get_args(hint), tuple) and len(type_args) > 0:
            origin_type = type_args[0] if inspect.isclass(type_args[0]) else get_origin(type_args[0])
            is_list = issubclass(origin_type, list)
        type_meta = next((x for x in type_args if isinstance(x, TypeMeta)), None)

        if len(type_args) > 1:
            while args := get_args(type_args[0]):
                type_args = args
        type_info = next((x for x in type_args if isinstance(x, TypeInfo)), None)
        base_type = next(iter(type_args), hint)

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
            elif issubclass(type_iterator.base_type, StructDataclass):
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
                # TODO: Should we make a special type to strictly bypass this stuff?
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

    def assign_decoded_values(self, data: list[int]) -> None:
        idx = 0

        for state in self._state:
            attr = getattr(self, state.name)

            if isinstance(attr, list) and isinstance(attr[0], StructDataclass):
                if not isinstance(attr, list):
                    continue

                list_idx = 0
                sub_struct_byte_length = attr[0].size()  # TODO: Fix warning here
                while list_idx < state.size:
                    attr[list_idx].assign_decoded_values(data[idx : idx + sub_struct_byte_length])
                    list_idx += 1
                    idx += sub_struct_byte_length
            elif isinstance(attr, StructDataclass):
                # TODO If state is != 1 then just break or something? I dunno
                if state.size == 1:
                    sub_struct_byte_length = attr.size()
                    attr.assign_decoded_values(data[idx : idx + sub_struct_byte_length])
                    idx += sub_struct_byte_length
                    continue
            else:
                if state.size == 1:
                    setattr(self, state.name, data[idx])
                    idx += 1
                    continue

                list_idx = 0
                while list_idx < state.size:
                    getattr(self, state.name)[list_idx] = data[idx]
                    list_idx += 1
                    idx += 1

    def decode(self, data: list[int] | bytes, little_endian=False) -> None:
        data = self._to_bytes(data)

        # Decode
        self.assign_decoded_values(list(struct.unpack(self._endian(little_endian) + self.struct_fmt, data)))

    def retrieve_values_to_encode(self) -> list[int]:
        result: list[int] = []

        for state in self._state:
            attr = getattr(self, state.name)

            if isinstance(attr, list) and isinstance(attr[0], StructDataclass):
                if not isinstance(attr, list):  # TODO: Get rid of this lol
                    continue

                for item in attr:
                    result.extend(item.retrieve_values_to_encode())
            elif isinstance(attr, StructDataclass):
                if state.size == 1:  # TODO: Do we need this? lol
                    result.extend(attr.retrieve_values_to_encode())
            else:
                if state.size == 1:
                    result.append(getattr(self, state.name))
                else:
                    result.extend(getattr(self, state.name))
        return result

    def encode(self, little_endian=False) -> bytes:
        result = self.retrieve_values_to_encode()
        return struct.pack(self._endian(little_endian) + self.struct_fmt, *result)


# TODO: BIG TODO LOOK AT THIS ONE!!!
# TODO: Determine if we actually need to use proper dataclasses?
# TODO: Is there some way I can instantiate the dataclass with some placeholder data and then replace it later?
# TODO: Having a hard time using fields with deferred default_factories for custom classes that don't exist yet
# TODO: Maybe I just abandon my hacky class bullshit, and make the users define fields themselves for defaults?


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


@overload
def struct_dataclass(_cls: type[StructDataclass]) -> Type[StructDataclass]: ...


@overload
def struct_dataclass(_cls: None) -> Callable[[type[StructDataclass]], Type[StructDataclass]]: ...


def struct_dataclass(
    _cls: type[StructDataclass] | None = None,
) -> Callable[[type[StructDataclass]], Type[StructDataclass]] | Type[StructDataclass]:
    def inner(_cls: type[StructDataclass]) -> type[StructDataclass]:
        new_cls = _cls

        # new_cls should not already be a dataclass
        if is_dataclass(new_cls):
            return cast(type[StructDataclass], new_cls)

        # defaults: dict[str, Any] = {}
        #
        # # Do a first pass where we just set sane defaults so dataclass doesn't get mad at us
        # for ti in iterate_types(new_cls):
        #     if not ti.is_pystructtype:
        #         continue
        #
        #     # Determine proper default for key
        #     defaults[ti.key] = ti.base_type
        #     if ti.type_meta and ti.type_meta.default:
        #         defaults[ti.key] = ti.type_meta.default
        #
        #     if not ti.type_meta or ti.type_meta.size == 1:
        #         if ti.is_list:
        #             raise Exception("size = 1, shouldn't be a list")
        #
        #         setattr(new_cls, ti.key, field(default=0))
        #     else:
        #         if not ti.is_list:
        #             raise Exception("this should be a list dunko")
        #
        #         setattr(new_cls, ti.key, field(default_factory=list))
        #
        # # TODO: Am I getting anything out of this being a dataclass?
        # newer_cls = dataclass(new_cls)
        #
        # return newer_cls

        # Make sure any fields without a default have one
        for type_iterator in iterate_types(new_cls):
            if not type_iterator.is_pystructtype:
                continue

            if not type_iterator.type_meta or type_iterator.type_meta.size == 1:
                if type_iterator.is_list:
                    raise Exception("You said this should be size 1, so this shouldn't be a list")

                # Set a default if it does not yet exist
                if not getattr(new_cls, type_iterator.key, None):
                    default = type_iterator.base_type
                    if type_iterator.type_meta and type_iterator.type_meta.default:
                        default = type_iterator.type_meta.default
                        if isinstance(default, list):
                            raise Exception("A default for a size 1 should not be a list")

                    # Create a new instance of the class
                    if inspect.isclass(default):
                        default = field(default_factory=lambda d=default: d())
                    else:
                        default = field(default_factory=lambda d=default: deepcopy(d))

                    setattr(
                        new_cls,
                        type_iterator.key,
                        default,
                    )
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
                            default_factory=lambda d=default, s=type_iterator.type_meta.size: [d() for _ in range(s)]
                        )
                    else:
                        default_list = field(
                            default_factory=lambda d=default, s=type_iterator.type_meta.size: [
                                deepcopy(d) for _ in range(s)
                            ]
                        )

                setattr(
                    new_cls,
                    type_iterator.key,
                    default_list,
                )
        return cast(type[StructDataclass], dataclass(new_cls))

    if _cls is None:
        return inner
    return inner(_cls)


class BitsType(StructDataclass):
    _raw: Any
    _meta: Any

    def assign_decoded_values(self, data: list[int]) -> None:
        # First call the super function to put the values in to _raw
        super().assign_decoded_values(data)

        # Combine all data in _raw as binary and convert to bools
        # TODO: Explain this bullshit and maybe make a helper function to turn bytes into lists of bools
        byte_size = self._byte_length
        bin_data = list(map(bool, map(int, format(self._raw, f"#0{(byte_size * 8) + 2}b")[2:][::-1])))

        for k, v in self._meta.items():
            if isinstance(v, list):
                steps = []
                for idx in v:
                    steps.append(bin_data[idx])
                setattr(self, k, steps)
            else:
                setattr(self, k, bin_data[v])

    def retrieve_values_to_encode(self) -> list[int]:
        bin_data = list(itertools.repeat(False, self._byte_length * 8))
        for k, v in self._meta.items():
            if isinstance(v, list):
                steps = getattr(self, k)
                for idx, bit_idx in enumerate(v):
                    bin_data[bit_idx] = steps[idx]
            else:
                bin_data[v] = getattr(self, k)

        self._raw = sum(v << i for i, v in enumerate(bin_data))

        # Run the super function to return the data in self._raw()
        return super().retrieve_values_to_encode()


def bits_cls(_type: type, definition: dict[str, int | list[int]]) -> Callable[[type[BitsType]], type[StructDataclass]]:
    def inner(_cls: type[BitsType]) -> type[StructDataclass]:
        # Create class attributes based on the definition
        # TODO: Maybe a sanity check to make sure the definition is the right format, and no overlapping bits, etc

        new_cls = _cls
        new_cls.__annotations__["_raw"] = _type  # TODO: Allow multiple bytes for the type?
        new_cls.__annotations__["_meta"] = dict[str, int]
        # TODO: Dunno if I need deepcopy here
        new_cls._meta = field(default_factory=eval(f"lambda: deepcopy({definition})"))

        # TODO: Support int as a default value, and map accordingly, also implement default properly
        for k, v in definition.items():
            if isinstance(v, list):
                setattr(
                    new_cls,
                    k,
                    field(default_factory=eval(f"lambda: [False for _ in range({len(v)})]")),
                )
                new_cls.__annotations__[k] = list[bool]
            else:
                setattr(new_cls, k, False)
                new_cls.__annotations__[k] = bool

        return struct_dataclass(new_cls)

    return inner


def bits(name: str, _type: type, definition: dict[str, int | list[int]]) -> type[StructDataclass]:
    # TODO: Figure out why this doesn't work with MYPY, very frustrating

    # For reference, the function *should* look like:
    # FlagsType = bits("FlagsType", uint8_t, {"autolights": 0, "fsr": 1})

    _cls = cast(type[BitsType], type(name, (BitsType,), {}))  # type: ignore
    new_cls = bits_cls(type, definition)(_cls)
    return cast(type[StructDataclass], new_cls)
