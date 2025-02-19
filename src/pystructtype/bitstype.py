import itertools
from collections.abc import Callable
from dataclasses import field
from typing import Any

from pystructtype.structdataclass import StructDataclass, struct_dataclass
from pystructtype.utils import int_to_bool_list, list_chunks


class BitsType(StructDataclass):
    """
    Class to auto-magically decode/encode struct data into separate variables
    for separate bits based on the given definition
    """

    _raw: Any
    _meta: dict
    _meta_tuple: tuple

    def __post_init__(self) -> None:
        super().__post_init__()

        # Convert the _meta_tuple data into a dictionary and put it into _meta
        self._meta = {k: v for k, v in zip(*self._meta_tuple, strict=False)}

    def _decode(self, data: list[int]) -> None:
        """
        Internal decoding function

        :param data: A list of ints to decode
        """
        # First call the super function to put the values in to _raw
        super()._decode(data)

        # Combine all data in _raw as binary and convert to bools
        bin_data = int_to_bool_list(self._raw, self._byte_length)

        # Apply bits to the defined structure
        for k, v in self._meta.items():
            if isinstance(v, list):
                steps = []
                for idx in v:
                    steps.append(bin_data[idx])
                setattr(self, k, steps)
            else:
                setattr(self, k, bin_data[v])

    def _encode(self) -> list[int]:
        """
        Internal encoding function

        :returns: A list of encoded ints
        """
        # Fill a correctly sized variable with all False/0 bits
        bin_data = list(itertools.repeat(False, self._byte_length * 8))

        # Assign the correct values from the defined attributes into bin_data
        for k, v in self._meta.items():
            if isinstance(v, list):
                steps = getattr(self, k)
                for idx, bit_idx in enumerate(v):
                    bin_data[bit_idx] = steps[idx]
            else:
                bin_data[v] = getattr(self, k)

        # Convert bin_data back into their correct integer locations
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
    """
    Decorator that does a bunch of metaprogramming magic to properly set up the
    defined Subclass of StructDataclass for Bits handling

    The definition must be a dict of ints or a list of ints. The int values denote the position of the bits.

    Example:
    @bits(uint8_t, {"a": 0, "b": [1, 2, 4], "c": 3})
    class MyBits(BitsType): ...

    For an uint8_t defined as 0b01010101, the resulting class will be:
    MyBits(a=1, b=[0, 1, 1], c=0)

    :param _type: The type of data that the bits are stored in (ex. uint8_t, etc.)
    :param definition: The bits definition that defines attributes and bit locations
    :return: A Callable that performs the metaprogramming magic and returns the modified StructDataclass
    """

    def inner(_cls: type[BitsType]) -> type[StructDataclass]:
        """
        The inner function to modify a StructDataclass into a BitsType class

        :param _cls: A Subclass of BitsType
        :return: Modified StructDataclass
        """
        # Create class attributes based on the definition
        # TODO: Maybe a sanity check to make sure the definition is the right format, and no overlapping bits, etc

        new_cls = _cls

        # Set the correct type for the raw data
        new_cls.__annotations__["_raw"] = _type

        # Override the annotations for the _meta attribute, and set a default
        # TODO: This probably isn't really needed unless we end up changing the int value to bool or something
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
        # Create the defined attributes, defaults, and annotations in the class
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
