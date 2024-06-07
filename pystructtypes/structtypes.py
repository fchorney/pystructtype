import inspect
import re
import struct
from copy import deepcopy

# import struct
from dataclasses import dataclass, field, is_dataclass
from typing import Annotated, Any, TypeAlias, TypeVar, Union, get_type_hints, get_args, get_origin


# Just so we have a fancy name
# StructList = Annotated

# Fixed Size Types
# int8_t: TypeAlias = Annotated[int, "b"]  # 1 Byte
# uint8_t: TypeAlias = Annotated[int, "B"]  # 1 Byte
# int16_t: TypeAlias = Annotated[int, "h"]  # 2 Bytes
# uint16_t: TypeAlias = Annotated[int, "H"]  # 2 Bytes
# int32_t: TypeAlias = Annotated[int, "i"]  # 4 Bytes
# uint32_t: TypeAlias = Annotated[int, "I"]  # 4 Bytes
# int64_t: TypeAlias = Annotated[int, "q"]  # 8 Bytes
# uint64_t: TypeAlias = Annotated[int, "Q"]  # 8 Bytes

# TODO: Commented types shadow built-ins, figure out a good way to change that ?

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

# TODO: Potentially make a `struct_dataclass` function that turns any args into kwargs with defaults?
# Look at https://github.com/tobywf/xml_dataclasses/blob/master/src/xml_dataclasses/resolve_types.py#L238


@dataclass
class StructState:
    name: str
    struct_fmt: str
    size: int


class StructDataclass:
    def __post_init__(self):
        self.__state: list[StructState] = []
        # Grab Struct Format
        self.struct_fmt = ""
        for key, hint in get_type_hints(self, include_extras=True).items():
            type_args = get_args(hint)
            base_typemeta = next((x for x in type_args if isinstance(x, TypeMeta)), None)

            while (args := get_args(type_args[0])):
                type_args = args
            base_typeinfo = next((x for x in type_args if isinstance(x, TypeInfo)), None)
            base_type = type_args[0]

            if not meta or not isinstance(meta[0], CStructType):
                sub_struct = getattr(self, key)
                if len(meta) > 1:
                    for sub in sub_struct:
                        self.struct_fmt += sub.struct_fmt
                        self.__state.append(StructState(key, meta[1]))
                else:
                    self.struct_fmt += sub_struct.struct_fmt
                    self.__state.append(StructState(key, sub_struct))
            else:
                meta = meta[0]
                self.struct_fmt += f"{meta.size if meta.size > 1 else ""}{meta.format}"
                self.__state.append(StructState(key, meta))
        print(self._simplify_format())
        print(self._byte_length())

    @classmethod
    def struct_format(cls) -> str:
        # Grab Struct Format
        struct_fmt = ""
        for key, hint in get_type_hints(cls, include_extras=True).items():
            meta = getattr(hint, "__metadata__", [])

            if not meta or not isinstance(meta[0], CStructType):
                sub_struct = getattr(cls, key)
                if len(meta) > 1:
                    for sub in sub_struct:
                        struct_fmt += sub.struct_fmt
                else:
                    struct_fmt += sub_struct.struct_fmt
            else:
                meta = meta[0]
                struct_fmt += f"{meta.size if meta.size > 1 else ""}{meta.format}"
        return struct_fmt

    @classmethod
    def byte_size(cls) -> int:
        return struct.calcsize("=" + cls.struct_format())

    def _byte_length(self, little_endian: bool = True) -> int:
        return struct.calcsize(self._endian(little_endian) + self.struct_fmt)

    @property
    def size(self) -> int:
        s = 0
        for state in self.__state:
            if isinstance(sub_struct := getattr(self, state.name), StructDataclass):
                s += sub_struct.size
            else:
                s += state.structtype.size
        return s

    def _simplify_format(self) -> str:
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
            simplified_format += f"{group_len if group_len > 1 else ""}{group[0]}"

        return simplified_format

    def _endian(self, little_endian: bool) -> str:
        return "<" if little_endian else ">"

    def _to_bytes(self, data: list[int] | bytes) -> bytes:
        if isinstance(data, bytes):
            return data
        return bytes(data)

    def _to_list(self, data: list[int] | bytes) -> list[int]:
        if isinstance(data, bytes):
            return list(data)
        return data

    def assign_decoded_values(self, data: list[int]):
        idx = 0

        for state in self.__state:
            if isinstance(sub_struct := getattr(self, state.name), StructDataclass):
                result_length = sub_struct.size
                sub_struct.assign_decoded_values(data[idx:idx + result_length])
                idx += result_length
            else:
                if state.structtype.size == 1:
                    setattr(self, state.name, data[idx])
                    idx += 1
                    continue

                list_idx = 0
                while list_idx < state.structtype.size:
                    getattr(self, state.name)[list_idx] = data[idx]
                    list_idx += 1
                    idx += 1

    def decode(self, data: list[int] | bytes, little_endian=False) -> None:
        data = self._to_bytes(data)

        # Decode
        self.assign_decoded_values(
            list(struct.unpack(self._endian(little_endian) + self.struct_fmt, data))
        )

    def retrieve_values_to_encode(self) -> list[int]:
        result = []

        for state in self.__state:
            if isinstance(sub_struct := getattr(self, state.name), StructDataclass):
                result.extend(sub_struct.retrieve_values_to_encode())
            else:
                if state.structtype.size == 1:
                    result.append(getattr(self, state.name))
                else:
                    result.extend(getattr(self, state.name))
        return result

    def encode(self, little_endian=False) -> bytes:
        result = self.retrieve_values_to_encode()
        return struct.pack(self._endian(little_endian) + self.struct_fmt, *result)


StructDataclassInstance = TypeVar("StructDataclassInstance", bound=StructDataclass)


def struct_dataclass(cls: type[StructDataclassInstance] | None = None, /, **kwargs):
    def inner(_cls: Any) -> type[StructDataclassInstance]:
        # If a dataclass is doubly decorated, metadata seems to disappear...
        if is_dataclass(_cls):
            new_cls = _cls
        else:
            # Make sure any fields without a default have one
            for k, v in inspect.get_annotations(_cls).items():
                # TODO: Can use typing.get_args, typing.get_origin, to figure out what we're dealing with here
                type_args = get_args(v)
                base_typemeta = next((x for x in type_args if isinstance(x, TypeMeta)), None)

                while (args := get_args(type_args[0])):
                    type_args = args
                base_typeinfo = next((x for x in type_args if isinstance(x, TypeInfo)), None)
                base_type = type_args[0]

                # TODO: I don't know that we care about typeinfo here actually
                if not base_typemeta or base_typemeta.size == 1:
                    # No type meta, or size is 1, we can assume it's not a list, and there is no
                    # specific default, so just instantiate it with the default value for
                    # the base type
                    setattr(_cls, k, base_type())

                print(1)
                # if not (metadata := getattr(v, "__metadata__", [])):
                #     if not issubclass(_cls, StructDataclass):
                #         # We should always have metadata here
                #         raise Exception("huh, where's the metadata?")
                #     # We have a StructDataclass subtype here
                #     setattr(_cls, k, field(default_factory=v))
                # elif not isinstance(metadata[0], CStructType):
                #     size, c = metadata
                #     setattr(
                #         _cls,
                #         k,
                #         field(
                #             default_factory=eval(
                #                 f"lambda: [{c.__name__}() for _ in range({size})]"
                #             )
                #         ),
                #     )
                # elif structmeta := metadata[0]:
                #     if structmeta.size <= 0:
                #         raise Exception("Size can't be zero or less")
                #
                #     if structmeta.size == 1:
                #         # Not a list
                #         if not getattr(_cls, k, None):
                #             setattr(_cls, k, structmeta.default)
                #     else:
                #         if not isinstance(structmeta.default, list):
                #             setattr(
                #                 _cls,
                #                 k,
                #                 field(
                #                     default_factory=eval(
                #                         f"lambda: [deepcopy({structmeta.default}) for _ in range({structmeta.size})]",
                #                     )
                #                 ),
                #             )
                #         else:
                #             setattr(
                #                 _cls,
                #                 k,
                #                 field(
                #                     default_factory=eval(
                #                         f"lambda: [x for x in {structmeta.default}]"
                #                     )
                #                 ),
                #             )
            new_cls = dataclass(**kwargs)(_cls)

        return new_cls

    # See if we're being called as @struct_dataclass or @struct_dataclass()
    if cls is None:
        # We're called with parens.
        return inner

    # We're called as @struct_dataclass without parens.
    return inner(cls)


all_struct_types: TypeAlias = int | float | bool | list[int] | list[float] | list[bool]


@dataclass
class CStructType:
    size: int
    default: all_struct_types | StructDataclass
    format: str
    byte_size: int


def uint8_t(size: int = 1, default: int | list[int] = 0x00) -> CStructType:
    return CStructType(size, default, "B", 1)


def uint16_t(size: int = 1, default: int | list[int] = 0x00) -> CStructType:
    return CStructType(size, default, "H", 2)


@dataclass
class TypeMeta:
    size: int
    default: Any


@dataclass
class TypeInfo:
    format: str
    byte_size: int


uint8_x: TypeAlias = Annotated[int, TypeInfo('B', 1)]


@struct_dataclass
class Beans(StructDataclass):
    nut: uint8_x

@struct_dataclass
class Gotem(StructDataclass):
    a: Annotated[list[uint8_x], TypeMeta(2, 0x0F)]
    b: uint8_x
    c: Annotated[uint8_x, TypeMeta(1, 0x0F)]
    d: Beans
    e: Annotated[list[Beans], TypeMeta(2, Beans(1))]


@struct_dataclass
class TestClass4(StructDataclass):
    f: Annotated[list[int], uint8_t(size=2, default=[0x00, 0xFF])]
    g: Annotated[int, uint8_t(default=0xFF)]
    h: Annotated[int, uint16_t(default=0xFFFF)]


@struct_dataclass
class TestClass3(StructDataclass):
    c: Annotated[list[int], uint8_t(size=4, default=[0x00, 0x0F, 0xF0, 0xFF])]
    d: Annotated[list[int], uint8_t(size=2)]
    e: Annotated[list[int], uint8_t(size=3, default=0xFF)]
    x: TestClass4


@struct_dataclass
class TestClass2(StructDataclass):
    a: Annotated[int, uint8_t()]
    b: Annotated[list[int], uint8_t(size=2, default=0x0F)]
    z: TestClass3


@struct_dataclass
class PackedPanelSettings_T(StructDataclass):
    load_cell_low_threshold: Annotated[int, uint8_t()]
    load_cell_high_threshold: Annotated[int, uint8_t()]

    fsr_low_threshold: Annotated[list[int], uint8_t(size=4)]
    fsr_high_threshold: Annotated[list[int], uint8_t(size=4)]

    combined_low_threshold: Annotated[int, uint16_t()]
    combined_high_threshold: Annotated[int, uint16_t()]

    reserved: Annotated[int, uint16_t()]


# TODO: how to implement bits struct?


@struct_dataclass
class RGB_T(StructDataclass):
    r: Annotated[int, uint8_t()]
    g: Annotated[int, uint8_t()]
    b: Annotated[int, uint8_t()]


def rgb_t(size: int = 1, default: RGB_T = RGB_T()) -> CStructType:
    return CStructType(size, default, RGB_T.struct_format(), RGB_T.byte_size())


def packed_panel_settings_t(
    size: int = 1, default: PackedPanelSettings_T = PackedPanelSettings_T()
) -> CStructType:
    return CStructType(
        size,
        default,
        PackedPanelSettings_T.struct_format(),
        PackedPanelSettings_T.byte_size(),
    )


@struct_dataclass
class SMXConfig_T(StructDataclass):
    master_version: Annotated[int, uint8_t(default=0xFF)]

    config_version: Annotated[int, uint8_t(default=0x05)]

    flags: Annotated[int, uint8_t(default=0b11)]  # TODO: Figure out a special bits type

    debounce_no_delay_milliseconds: Annotated[int, uint16_t(default=0)]
    debounce_delay_milliseconds: Annotated[int, uint16_t(default=0)]
    panel_debounce_microseconds: Annotated[int, uint16_t(default=4000)]
    auto_calibration_max_deviation: Annotated[int, uint8_t(default=100)]
    bad_sensor_minimum_delay_seconds: Annotated[int, uint8_t(default=15)]
    auto_calibration_averages_per_update: Annotated[int, uint16_t(default=60)]
    auto_calibration_samples_per_average: Annotated[int, uint16_t(default=500)]

    auto_calibration_max_tare: Annotated[int, uint16_t(default=0xFFFF)]

    enabled_sensors: Annotated[
        list[int], uint8_t(size=5)
    ]  # TODO: Come up with enabled_sensors struct

    auto_lights_timeout: Annotated[int, uint8_t(default=1000 // 128)]

    step_color: Annotated[
        list[RGB_T], rgb_t(size=9)
    ]  # TODO: Need to handle lists of StructDataclasses

    platform_strip_color: RGB_T

    auto_light_panel_mask: Annotated[
        int, uint16_t(default=0xFFFF)
    ]  # TODO: This could be a bit mask object?

    panel_rotation: Annotated[int, uint8_t(default=0x00)]

    packed_panel_settings: Annotated[
        list[PackedPanelSettings_T], packed_panel_settings_t(size=9)
    ]

    pre_details_delay_milliseconds: Annotated[int, uint8_t(default=0x05)]

    padding: Annotated[list[int], uint8_t(size=49)]
