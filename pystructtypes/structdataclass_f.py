import inspect
import re
import struct
from copy import deepcopy  # noqa
from dataclasses import dataclass, field, is_dataclass
from typing import Annotated, Any, Generator, get_args, get_origin, get_type_hints


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

    @property
    def size(self):
        return getattr(self.type_meta, "size", 1)


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

        yield TypeIterator(key, base_type, type_info, type_meta, is_list)


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
        for type_iterator in iterate_types(self):
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


def struct_dataclass(cls: type[StructDataclass] | None = None, /, **kwargs):
    def inner(_cls: Any) -> type[StructDataclass]:
        # If a dataclass is doubly decorated, metadata seems to disappear...
        if is_dataclass(_cls):
            new_cls = _cls
        else:
            # Make sure any fields without a default have one
            for type_iterator in iterate_types(_cls):
                if not type_iterator.type_meta or type_iterator.type_meta.size == 1:
                    # No type meta, or size is 1, we can assume it's not a list, and there is no
                    # specific default, so just instantiate it with the default value for
                    # the base type
                    if not getattr(_cls, type_iterator.key, None):
                        default = (
                            type_iterator.type_meta.default
                            if (type_iterator.type_meta and type_iterator.type_meta.default)
                            else type_iterator.base_type()
                        )
                        setattr(
                            _cls,
                            type_iterator.key,
                            field(default_factory=eval(f"lambda: deepcopy({default})")),
                        )
                else:
                    # This assumes we want multiple items of base_type, so make sure the given base_type is
                    # properly set to be a list as well
                    if not type_iterator.is_list:
                        raise Exception("You want a list, so make it a list you dummy")
                    # We have a meta type and the size is > 1 so make the default a field
                    default = (
                        type_iterator.type_meta.default
                        if (type_iterator.type_meta and type_iterator.type_meta.default)
                        else type_iterator.base_type()
                    )
                    setattr(
                        _cls,
                        type_iterator.key,
                        field(
                            default_factory=eval(
                                f"lambda: [deepcopy({default}) for _ in range({type_iterator.type_meta.size})]"
                            )
                        ),
                    )
            new_cls = dataclass(**kwargs)(_cls)
        return new_cls

    # See if we're being called as @struct_dataclass or @struct_dataclass()
    if cls is None:
        # We're called with parens.
        return inner

    # We're called as @struct_dataclass without parens.
    return inner(cls)
