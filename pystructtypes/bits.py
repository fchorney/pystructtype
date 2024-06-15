import itertools
from copy import deepcopy  # noqa
from dataclasses import field
from typing import Any, Callable, cast

from pystructtypes.structdataclass_f import StructDataclass, struct_dataclass


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
