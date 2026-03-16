import itertools
from collections.abc import Mapping
from dataclasses import field
from types import MappingProxyType
from typing import Annotated, ClassVar

from pystructtype.structdataclass import StructDataclass
from pystructtype.structtypes import TypeMeta
from pystructtype.utils import int_to_bool_list


class BitsType(StructDataclass):
    """
    Base class for bitfield structs. Subclasses must define __bits_type__ and __bits_definition__.
    """

    __bits_type__: ClassVar[type]
    __bits_definition__: ClassVar[dict[str, int | list[int]] | Mapping[str, int | list[int]]]

    _raw: int
    _meta: dict[str, int | list[int]]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Check for required attributes
        if not hasattr(cls, "__bits_type__") or not hasattr(cls, "__bits_definition__"):
            raise TypeError(
                "Subclasses of BitsType must define __bits_type__ and __bits_definition__ class attributes."
            )
        bits_type = cls.__bits_type__
        definition = cls.__bits_definition__

        # Automatically wrap in MappingProxyType if it's a dict and not already immutable
        if isinstance(definition, dict) and not isinstance(definition, MappingProxyType):
            definition = MappingProxyType(definition)
            cls.__bits_definition__ = definition

        # # Remove __bits_type__ and __bits_definition__ from __annotations__ if present
        # cls.__annotations__.pop("__bits_type__", None)
        # cls.__annotations__.pop("__bits_definition__", None)

        # Set the correct type for the raw data
        cls._raw = 0
        cls.__annotations__["_raw"] = bits_type

        cls._meta = field(default_factory=dict)

        # Create the defined attributes, defaults, and annotations in the class
        for key, value in definition.items():
            if isinstance(value, list):
                setattr(
                    cls,
                    key,
                    field(default_factory=lambda v=len(value): [False for _ in range(v)]),  # type: ignore
                )
                cls.__annotations__[key] = Annotated[list[bool], TypeMeta(size=len(value))]
            else:
                setattr(cls, key, False)
                cls.__annotations__[key] = bool

    def __post_init__(self) -> None:
        super().__post_init__()
        self._meta = dict(self.__bits_definition__)

    def _decode(self, data: list[int]) -> None:
        super()._decode(data)
        bin_data = int_to_bool_list(self._raw, self._byte_length)
        for k, v in self._meta.items():
            if isinstance(v, list):
                steps = [bin_data[idx] for idx in v]
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
        self._raw = sum(int(v) << i for i, v in enumerate(bin_data))
        # Return _raw as a list of bytes (little-endian)
        return super()._encode()
