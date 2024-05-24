from dataclasses import dataclass, field, is_dataclass, fields
import struct
from typing import Annotated, get_type_hints, TypeAlias, Type, TypeVar, Any, Generic

# Just so we have a fancy name
StructList = Annotated

# Fixed Size Types
int8_t: TypeAlias = Annotated[int, 'b']  # 1 Byte
uint8_t: TypeAlias = Annotated[int, 'B']  # 1 Byte
int16_t: TypeAlias = Annotated[int, 'h']  # 2 Bytes
uint16_t: TypeAlias = Annotated[int, 'H']  # 2 Bytes
int32_t: TypeAlias = Annotated[int, 'i']  # 4 Bytes
uint32_t: TypeAlias = Annotated[int, 'I']  # 4 Bytes
int64_t: TypeAlias = Annotated[int, 'q']  # 8 Bytes
uint64_t: TypeAlias = Annotated[int, 'Q']  # 8 Bytes

# TODO: Commented types shadow built-ins, figure out a good way to change that ?

# Named Types
char: TypeAlias = Annotated[int, 'b']  # 1 Byte
unsigned_char: TypeAlias = Annotated[int, 'B']  # 1 Byte
# bool: TypeAlias = Annotated[int, '?']  # 1 Byte
short: TypeAlias = Annotated[int, 'h']  # 2 Bytes
unsigned_short: TypeAlias = Annotated[int, 'H']  # 2 Bytes
# int: TypeAlias = Annotated[int, 'i']  # 4 Bytes
unsigned_int: TypeAlias = Annotated[int, 'I']  # 4 Bytes
long: TypeAlias = Annotated[int, 'l']  # 4 Bytes
unsigned_long: TypeAlias = Annotated[int, 'L']  # 4 Bytes
long_long: TypeAlias = Annotated[int, 'q']  # 8 Bytes
unsigned_long_long: TypeAlias = Annotated[int, 'Q']  # 8 Bytes
# float: TypeAlias = Annotated[float, 'f']  # 4 Bytes
double: TypeAlias = Annotated[float, 'd']  # 8 Bytes


@dataclass
class StructClassState[T]:
    name: str
    # TODO: This probably doesn't need to be a generic T? We'll see
    default_value: T
    is_list: bool
    list_length: int


# TODO: Potentially make a `struct_dataclass` function that turns any args into kwargs with defaults?
# Look at https://github.com/tobywf/xml_dataclasses/blob/master/src/xml_dataclasses/resolve_types.py#L238

class StructDataclass:
    pass

StructDataclassInstance = TypeVar("StructDataclassInstance", bound=StructDataclass)

def struct_dataclass(cls: Type[Any]) -> Type[StructDataclassInstance]:
    # If a dataclass is doubly decorated, metadata seems to disappear...
    if is_dataclass(cls):
        new_cls = cls
    else:
        new_cls = dataclass()(cls)

    type_hints = get_type_hints(cls, include_extras=True)
    for f in fields(cls):
        # If there is no default
        pass

    return new_cls


class SubscriptableType():
    BASE_TYPE: Any = Any
    FORMAT: str = ""

    @classmethod
    def __class_getitem__(cls, param: Any) -> "SubscriptableType":
        if not isinstance(param, tuple):
            return cls()
        return cls()

class Int8(SubscriptableType):
    BaseType = int
    FORMAT = 'b'

@struct_dataclass
class TestClass():
    x: Int8
    a: Int8[2, 0x0F]
    b: StructList[uint8_t, 2] = field(default_factory=list)
    c: uint16_t = 0
    d: uint8_t = 0
    e: StructList[uint16_t, 3, 0xFFFF] = field(default_factory=list)

@dataclass
class StructClass(object):
    __state: list[StructClassState] = field(default_factory=list)

    def __post_init__(self):
        # Grab Struct Format
        self.struct_fmt = ""
        for arg, hint in get_type_hints(self, include_extras=True).items():
            meta = getattr(hint, '__metadata__', [])

            if not meta:
                # TODO: Probably fail here or something?
                continue

            list_length = 0
            # If not set, default value is 0
            default_value = 0
            if is_list := ((metalen := len(meta)) >= 2):
                if not isinstance(getattr(self, arg, None), list):
                    # TODO: Raise some error probably
                    continue

                if metalen >= 3:
                    default_value = meta[2]
                setattr(self, arg, [default_value for _ in range(meta[1])])

                list_length = meta[1]
                self.struct_fmt += str(list_length)

            self.struct_fmt += meta[0]
            self.__state.append(StructClassState(arg, default_value, is_list, list_length))

    def decode(self, data: list[int], little_endian=False) -> None:
        # Decode
        endian = "<" if little_endian else ">"
        result = struct.unpack(endian + self.struct_fmt, bytes(data))
        idx = 0

        for state in self.__state:
            if not state.is_list:
                setattr(self, state.name, result[idx])
                idx += 1
                continue

            list_idx = 0
            while list_idx < state.list_length:
                getattr(self, state.name)[list_idx] = result[idx]
                list_idx += 1
                idx += 1
        print(1)

    def encode(self, little_endian=False) -> list[int]:
        result = []

        for state in self.__state:
            if not state.is_list:
                result.append(getattr(self, state.name))
            else:
                result.extend(getattr(self, state.name))

        endian = "<" if little_endian else ">"
        return list(struct.pack(endian + self.struct_fmt, *result))


@dataclass
class SMXConfig(StructClass):
    # TODO: Figure out a way not to have to use a `field` for default lists
    a: StructList[uint8_t, 2, 0x0F] = field(default_factory=list)
    b: StructList[uint8_t, 2] = field(default_factory=list)
    c: uint16_t = 0
    d: uint8_t = 0
    e: StructList[uint16_t, 3, 0xFFFF] = field(default_factory=list)
