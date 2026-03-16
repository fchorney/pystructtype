import inspect
import re
import struct
from copy import deepcopy
from dataclasses import dataclass, field, is_dataclass
from typing import ClassVar

from pystructtype.structtypes import iterate_types


@dataclass
class StructState:
    """
    Contains necessary struct information to correctly
    decode and encode the data in a StructDataclass
    """

    name: str
    struct_fmt: str
    size: int
    chunk_size: int


class StructDataclass:
    """
    Class that will auto-magically decode and encode data for the defined
    subclass.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # If the class is already a dataclass, skip
        if is_dataclass(cls):
            return
        # Make sure any fields without a default have one
        for type_iterator in iterate_types(cls):
            if type_iterator.key.startswith("__"):
                # Ignore double underscore vars
                continue

            if not type_iterator.is_pystructtype and not inspect.isclass(type_iterator.base_type):
                continue
            if not type_iterator.type_meta or type_iterator.type_meta.size == 1:
                if type_iterator.is_list:
                    raise ValueError(f"Attribute {type_iterator.key} is defined as a list type but has size set to 1")
                if not getattr(cls, type_iterator.key, None):
                    default = type_iterator.base_type
                    if type_iterator.type_meta:
                        if type_iterator.type_meta.default is not None:
                            default = type_iterator.type_meta.default
                            if isinstance(default, list):
                                raise TypeError(f"default value for {type_iterator.key} attribute can not be a list")
                            if inspect.isclass(default):
                                default = field(default_factory=default)
                                setattr(cls, type_iterator.key, default)
                                continue
                    if inspect.isclass(default):
                        default = field(default_factory=default)
                    else:
                        default = field(default_factory=lambda d=default: deepcopy(d))  # type: ignore
                    setattr(cls, type_iterator.key, default)
            else:
                if not type_iterator.is_list:
                    raise ValueError(f"Attribute {type_iterator.key} is not a list type but has a size > 1")
                if type_iterator.type_meta and type_iterator.type_meta.default:
                    default = type_iterator.type_meta.default
                    if isinstance(default, list):
                        default_tuple = tuple(deepcopy(default))
                        default_list = field(default_factory=lambda d=default_tuple: list(d))  # type: ignore
                    elif inspect.isclass(default):
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
                else:
                    default = type_iterator.base_type
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
                setattr(cls, type_iterator.key, default_list)
        # Remove ClassVar-annotated keys from __annotations__ and class dict before dataclass(cls)
        classvar_keys = [k for k, v in list(cls.__annotations__.items()) if getattr(v, "__origin__", None) is ClassVar]
        # Save and remove from class dict
        classvar_backup = {}
        for k in classvar_keys:
            cls.__annotations__.pop(k, None)
            if hasattr(cls, k):
                classvar_backup[k] = getattr(cls, k)
                delattr(cls, k)
        dataclass(cls)
        # Restore classvars
        for k, v in classvar_backup.items():
            setattr(cls, k, v)

    def __post_init__(self) -> None:
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
                        type_iterator.chunk_size,
                    )
                )
                _fmt_prefix = type_iterator.chunk_size if type_iterator.chunk_size > 1 else ""
                self.struct_fmt += f"{_fmt_prefix}{type_iterator.type_info.format}" * type_iterator.size
            elif inspect.isclass(type_iterator.base_type) and issubclass(type_iterator.base_type, StructDataclass):
                attr = getattr(self, type_iterator.key)
                if type_iterator.is_list:
                    fmt = attr[0].struct_fmt
                else:
                    fmt = attr.struct_fmt
                self._state.append(StructState(type_iterator.key, fmt, type_iterator.size, type_iterator.chunk_size))
                self.struct_fmt += fmt * type_iterator.size
            else:
                # We have no TypeInfo object, and we're not a StructDataclass
                # This means we're a regularly defined class variable, and we
                # Don't have to do anything about this.
                pass
        self._simplify_format()
        self._byte_length = struct.calcsize("=" + self.struct_fmt)
        # print(f"{self.__class__.__name__}: {self._byte_length} : {self.struct_fmt}")

    def _simplify_format(self) -> None:
        """
        Simplify the struct format that has been defined for this class.

        Essentially we turn things like `ccbbbbh` into `2c4bh`
        """
        # Expand any already condensed sections
        # This can happen if we have nested StructDataclasses
        expanded_format = ""
        items = re.findall(r"([a-zA-Z]|\d+)", self.struct_fmt)
        items_len = len(items)
        idx = 0
        while idx < items_len:
            if "0" <= (item := items[idx]) <= "9":
                idx += 1

                if items[idx] == "s":
                    # Shouldn't expand actual char[]/string types as they need to be grouped
                    # so we know how big the strings should be
                    expanded_format += item + items[idx]
                else:
                    expanded_format += items[idx] * int(item)
            else:
                expanded_format += item
            idx += 1

        # Simplify the format by turning multiple consecutive letters into a number + letter combo
        simplified_format = ""
        for group in (x[0] for x in re.findall(r"(\d*([a-zA-Z])\2*)", expanded_format)):
            if re.match(r"\d+", group[0]):
                # Just pass through any format that we've explicitly kept
                # a number in front of
                simplified_format += group
                continue

            simplified_format += f"{group_len if (group_len := len(group)) > 1 else ''}{group[0]}"

        self.struct_fmt = simplified_format

    def size(self) -> int:
        """
        The size of this struct is defined as the sum of the sizes of all attributes

        :return: Combined size of the struct
        """
        return sum(state.size for state in self._state)

    @staticmethod
    def _endian(little_endian: bool) -> str:
        """
        Return "<" or ">" depending on endianness, to pass to struct decode/encode

        :param little_endian: True if we expect little_endian, else False
        :return: "<" if little_endian else ">"
        """
        return "<" if little_endian else ">"

    @staticmethod
    def _to_bytes(data: list[int] | bytes) -> bytes:
        """
        Convert a list of ints into bytes

        :param data: a list of ints or a bytes object
        :return: a bytes object
        """
        if isinstance(data, bytes):
            return data
        return bytes(data)

    @staticmethod
    def _to_list(data: list[int] | bytes) -> list[int]:
        """
        Convert a bytes object into a list of ints

        :param data: a list of ints or a bytes object
        :return: a list of ints
        """
        if isinstance(data, bytes):
            return list(data)
        return data

    def _decode(self, data: list[int]) -> None:
        """
        Internal decoding function for the StructDataclass.

        Extend this function if you wish to add extra processing to your StructDataclass decoding processing

        :param data: A list of ints to decode into the StructDataclass
        """
        idx = 0
        for state in self._state:
            attr = getattr(self, state.name)

            if isinstance(attr, list) and isinstance(attr[0], StructDataclass):
                # If the current attribute is a list, and contains subclasses of StructDataclass
                # Call _decode on the required subset of bytes for each list item
                list_idx = 0
                sub_struct_byte_length = attr[0].size()
                while list_idx < state.size:
                    instance: StructDataclass = attr[list_idx]
                    instance._decode(data[idx : idx + sub_struct_byte_length])
                    list_idx += 1
                    idx += sub_struct_byte_length
            elif isinstance(attr, StructDataclass):
                # If the current attribute is not a list, and is a subclass of StructDataclass
                # Call _decode on the required subset of bytes for the item
                sub_struct_byte_length = attr.size()
                attr._decode(data[idx : idx + sub_struct_byte_length])
                idx += sub_struct_byte_length
            elif state.size == 1:
                # The current attribute is a base type of size 1
                setattr(self, state.name, data[idx])
                idx += 1
            else:
                # The current attribute is a list of base types
                list_idx = 0
                while list_idx < state.size:
                    getattr(self, state.name)[list_idx] = data[idx]
                    list_idx += 1
                    idx += 1

    def decode(self, data: list[int] | bytes, little_endian: bool = False) -> None:
        """
        Decode the given data into this subclass of StructDataclass

        :param data: list of ints or a bytes object
        :param little_endian: True if decoding little_endian formatted data, else False
        """
        data = self._to_bytes(data)

        # Decode
        self._decode(list(struct.unpack(self._endian(little_endian) + self.struct_fmt, data)))

    def _encode(self) -> list[int]:
        """
        Internal encoding function for the StructDataclass.

        Extend this function if you wish to add extra processing to your StructDataclass encoding processing

        :return: list of encoded int data
        """
        result: list[int] = []

        for state in self._state:
            attr = getattr(self, state.name)

            if isinstance(attr, list) and isinstance(attr[0], StructDataclass):
                # Attribute is a list of StructDataclass subclasses.
                # Simply call _encode on each item in the list
                item: StructDataclass
                for item in attr:
                    result.extend(item._encode())
            elif isinstance(attr, StructDataclass):
                # Attribute is a StructDataclass subclass
                # Call _encode on it
                result.extend(attr._encode())
            elif state.size == 1:
                # Attribute is a single base type
                # Append it to the result
                result.append(getattr(self, state.name))
            else:
                # Attribute is a list of base types
                # Extend it to the result
                result.extend(getattr(self, state.name))
        return result

    def encode(self, little_endian: bool = False) -> bytes:
        """
        Encode the data from this subclass of StructDataclass into bytes

        :param little_endian: True if encoding little_endian formatted data, else False
        :return: encoded bytes
        """
        result = self._encode()
        return struct.pack(self._endian(little_endian) + self.struct_fmt, *result)
