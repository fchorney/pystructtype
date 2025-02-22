import inspect
import re
import struct
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field, is_dataclass
from typing import cast, overload

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
                if state.size != 1:
                    raise Exception(f"Attribute {state.name} is not defined as a list but has a size > 0")

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

    def decode(self, data: list[int] | bytes, little_endian=False) -> None:
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
                if state.size != 1:
                    raise Exception(f"Attribute {state.name} is defined as a list but has a size == 1")
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

    def encode(self, little_endian=False) -> bytes:
        """
        Encode the data from this subclass of StructDataclass into bytes

        :param little_endian: True if encoding little_endian formatted data, else False
        :return: encoded bytes
        """
        result = self._encode()
        return struct.pack(self._endian(little_endian) + self.struct_fmt, *result)


@overload
def struct_dataclass(_cls: type[StructDataclass]) -> type[StructDataclass]:
    """
    Overload for using a bare decorator

    @struct_dataclass
    class foo(StructDataclass): ...

    Equivalent to: struct_dataclass(foo)

    :param _cls: Subtype of StructDataclass
    :return: Modified Subtype of StructDataclass
    """
    pass


@overload
def struct_dataclass(_cls: None) -> Callable[[type[StructDataclass]], type[StructDataclass]]:
    """
    Overload for using called decorator

    @struct_dataclass()
    class foo(StructDataclass): ...

    Equivalent to: struct_dataclass()(foo)

    :param _cls: None
    :return: Callable that takes in a Subtype of StructDataclass and returns a modified Subtype
    """
    pass


def struct_dataclass(
    _cls: type[StructDataclass] | None = None,
) -> Callable[[type[StructDataclass]], type[StructDataclass]] | type[StructDataclass]:
    """
    Decorator that does a bunch of metaprogramming magic to properly set up
    the defined Subclass of a StructDataclass

    :param _cls: A Subclass of StructDataclass or None
    :return: A Modified Subclass of a StructDataclass or a Callable that performs the same actions
    """

    def inner(_cls: type[StructDataclass]) -> type[StructDataclass]:
        """
        The inner function for `struct_dataclass` that actually does all the work

        :param _cls: A Subclass of StructDataclass
        :return: A Modified Subclass of a StructDataclass
        """
        new_cls = _cls

        # new_cls should not already be a dataclass,
        # but it will be a subtype of Dataclass by the end of this function
        if is_dataclass(new_cls):
            # Just try to cast it again, and return
            return cast(type[StructDataclass], new_cls)

        # Make sure any fields without a default have one
        # This prevents Dataclass from being mad that we might have attributes defined with
        # defaults interwoven between ones that don't
        for type_iterator in iterate_types(new_cls):
            # If the current type is just a base type, then we can essentially ignore it
            # These are typically used for extra processing and not included in the decode/encode
            if not type_iterator.is_pystructtype:
                continue

            if not type_iterator.type_meta or type_iterator.type_meta.size == 1:
                # This type either has no metadata, or is defined as having a size of 1 and is
                # therefore not a list
                if type_iterator.is_list:
                    raise Exception(f"Attribute {type_iterator.key} is defined as a list type but has size set to 1")

                # Set a default if it does not yet exist
                if not getattr(new_cls, type_iterator.key, None):
                    default: type | int | float = type_iterator.base_type
                    if type_iterator.type_meta and type_iterator.type_meta.default:
                        default = type_iterator.type_meta.default
                        if isinstance(default, list):
                            raise Exception(f"default value for {type_iterator.key} attribute can not be a list")

                    # Create a new instance of the class, or value
                    if inspect.isclass(default):
                        default = field(default_factory=lambda d=default: d())  # type: ignore
                    else:
                        default = field(default_factory=lambda d=default: deepcopy(d))  # type: ignore

                    setattr(new_cls, type_iterator.key, default)
            else:
                # This assumes we want multiple items of base_type, so make sure the given base_type is
                # properly set to be a list as well
                if not type_iterator.is_list:
                    raise Exception(f"Attribute {type_iterator.key} is not a list type but has a size > 1")

                # We have a meta type and the size is > 1 so make the default a field
                default = type_iterator.base_type
                if type_iterator.type_meta and type_iterator.type_meta.default:
                    default = type_iterator.type_meta.default

                default_list = []
                if isinstance(default, list):
                    # TODO: Implement having the entire list be a default rather than needing to set each
                    # TODO: element as the same base object.
                    pass
                else:
                    # Create a new instance of the class or value
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

    # If we use the decorator with empty parens, we simply return the inner callable
    if _cls is None:
        return inner

    # If we use the decorator with no parens, we return the result of passing the _cls
    # to the inner callable
    return inner(_cls)
