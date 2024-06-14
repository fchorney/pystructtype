import inspect
import itertools
import re
import struct
from collections.abc import Generator
from copy import copy, deepcopy  # noqa

# import struct
from dataclasses import dataclass, field, is_dataclass
from typing import Annotated, Any, Callable, cast, get_args, get_origin, get_type_hints


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
            simplified_format += f"{group_len if group_len > 1 else ""}{group[0]}"

        self.struct_fmt = simplified_format

    def _size(self) -> int:
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

            if (isinstance(attr, list) and isinstance(attr[0], StructDataclass)) or isinstance(attr, StructDataclass):
                if state.size == 1:
                    sub_struct_byte_length = attr._size()
                    attr.assign_decoded_values(data[idx : idx + sub_struct_byte_length])
                    idx += sub_struct_byte_length
                    continue

                if not isinstance(attr, list):
                    continue

                list_idx = 0
                sub_struct_byte_length = attr[0]._size()  # TODO: Fix warning here
                while list_idx < state.size:
                    attr[list_idx].assign_decoded_values(data[idx : idx + sub_struct_byte_length])
                    list_idx += 1
                    idx += sub_struct_byte_length
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

            if (isinstance(attr, list) and isinstance(attr[0], StructDataclass)) or isinstance(attr, StructDataclass):
                if state.size == 1:
                    result.extend(attr.retrieve_values_to_encode())
                else:
                    if not isinstance(attr, list):  # TODO: Get rid of this lol
                        continue

                    for item in attr:
                        result.extend(item.retrieve_values_to_encode())
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


@struct_dataclass
class PackedPanelSettingsType(StructDataclass):
    load_cell_low_threshold: uint8_t
    load_cell_high_threshold: uint8_t

    fsr_low_threshold: Annotated[list[uint8_t], TypeMeta(size=4)]
    fsr_high_threshold: Annotated[list[uint8_t], TypeMeta(size=4)]

    combined_low_threshold: uint16_t
    combined_high_threshold: uint16_t

    reserved: uint16_t


@struct_dataclass
class RGBType(StructDataclass):
    r: uint8_t
    g: uint8_t
    b: uint8_t


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


def bits(
    *args: type[BitsType] | str | type | dict[str, int | list[int]]
) -> Callable[[type[BitsType]], type[StructDataclass]] | type[StructDataclass]:
    _cls: type[BitsType] | None = None
    _type: type = uint8_t
    definition: dict[str, int | list[int]] = {}

    if len(args) == 2:
        _type, definition = args
        assert isinstance(type_from_annotation(_type), type)
        assert isinstance(definition, dict)
    elif len(args) == 3:
        name, _type, definition = args
        assert isinstance(name, str)
        assert isinstance(type_from_annotation(_type), type)
        assert isinstance(definition, dict)

        _cls = cast(type[BitsType], type(name, (BitsType,), {}))
    else:
        raise Exception("You have to pass two or three arguments. GOT IT?!")

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

    if _cls:
        return inner(_cls)
    return inner


FlagsType: type[StructDataclass] = bits("FlagsType", uint8_t, {"autolights": 0, "fsr": 1})
FT: type = FlagsType


@bits(uint16_t, {"_steps": [0, 1, 2, 3, 4, 5, 6, 7, 8]})
class PanelMaskType(BitsType):
    def __getitem__(self, index: int) -> bool:
        # This lets us access the data with square brackets
        # ex. `config.PanelMaskType[Panel.UP]`
        return getattr(self, "_steps", [])[index]

    def __setitem__(self, index: int, value: bool) -> None:
        # This lets us set the data with square brackets
        # ex. `config.PanelMaskType[Panel.DOWN] = True`
        steps = getattr(self, "_steps", [])
        assert index <= len(steps)
        steps[index] = value


# TODO: Make a BitField type


@struct_dataclass
class EnabledSensors(StructDataclass):
    # We can define the actual data we are ingesting here
    _raw: Annotated[list[uint8_t], TypeMeta(size=5)]

    # We use this to store the data in the way we actually want
    _data: list[list[bool]] = field(default_factory=list)

    def assign_decoded_values(self, data: list[int]) -> None:
        # First call the super function to put the values in to _raw
        super().assign_decoded_values(data)

        # Erase everything in self._data to remove any old data
        self._data = []

        # 2 Panels are packed into a single uint8_t, the left most 4 bits for the first
        # and the right most 4 bits for the second
        for bitlist in (list(map(bool, map(int, format(_byte, "#010b")[2:]))) for _byte in self._raw):
            self._data.append(bitlist[0:4])
            self._data.append(bitlist[4:])

        # Remove the last item in self._data as there are only 9 panels
        del self._data[-1]

    def retrieve_values_to_encode(self) -> list[int]:
        # Modify self._raw with updates values from self._data
        for idx, items in enumerate(list_chunks(self._data, 2)):
            # Last chunk
            if len(items) == 1:
                items.append([False, False, False, False])
            self._raw[idx] = sum(v << i for i, v in enumerate(list(itertools.chain.from_iterable(items))[::-1]))
        # Run the super function to return the data in self._raw()
        return super().retrieve_values_to_encode()

    def __getitem__(self, index: int) -> list[bool]:
        # This let's us access the data with square brackets
        # ex. `config.enabled_sensors[Panel.UP][Sensor.RIGHT]`
        return self._data[index]

    def __setitem__(self, index: int, value: list[bool]) -> None:
        # Only use this to set a complete set for a panel
        # ex. `config.enabled_sensors[Panel.UP] = [True, True, False, True]`
        if len(value) != 4 or not all(isinstance(x, bool) for x in value):
            raise Exception("use the right type of data scrub")
        self._data[index] = value


@struct_dataclass
class SMXConfigType(StructDataclass):
    master_version: uint8_t = 0xFF

    config_version: uint8_t = 0x05

    flags: FT

    debounce_no_delay_milliseconds: uint16_t = 0
    debounce_delay_milliseconds: uint16_t = 0
    panel_debounce_microseconds: uint16_t = 4000
    auto_calibration_max_deviation: uint8_t = 100
    bad_sensor_minimum_delay_seconds: uint8_t = 15
    auto_calibration_averages_per_update: uint16_t = 60
    auto_calibration_samples_per_average: uint16_t = 500

    auto_calibration_max_tare: uint16_t = 0xFFFF

    enabled_sensors: EnabledSensors

    auto_lights_timeout: uint8_t = 1000 // 128

    step_color: Annotated[list[RGBType], TypeMeta(size=9)]

    platform_strip_color: RGBType

    auto_light_panel_mask: PanelMaskType

    panel_rotation: uint8_t = 0x00

    packed_panel_settings: Annotated[list[PackedPanelSettingsType], TypeMeta(size=9)]

    pre_details_delay_milliseconds: uint8_t = 0x05

    padding: Annotated[list[uint8_t], TypeMeta(size=49)]
