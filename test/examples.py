import itertools
from dataclasses import field
from enum import IntEnum
from typing import Annotated

from pystructtype import BitsType, StructDataclass, TypeMeta, bits, struct_dataclass, uint8_t, uint16_t
from pystructtype.utils import list_chunks

TEST_CONFIG_DATA = [
    # masterVersion
    5,
    # configVersion
    5,
    # flags
    3,
    # debounceNodelayMilliseconds
    15,
    0,
    # debounceDelayMilliseconds
    0,
    0,
    # panelDebounceMicroseconds
    160,
    15,
    # autoCalibrationMaxDeviation
    100,
    # badSensorMinimumDelaySeconds
    15,
    # autoCalibrationAveragesPerUpdate
    44,
    1,
    # autoCalibrationSamplesPerAverage
    100,
    0,
    # autoCalibrationMaxTare
    255,
    255,
    # enabledSensors[5]
    15,
    15,
    15,
    15,
    0,
    # autoLightsTimeout
    7,
    # stepColor[3 * 9]
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    170,
    # platformStripColor[3]
    0,
    72,
    143,
    # autoLightPanelMask
    170,
    0,
    # panelRotation
    0,
    # panelSettings[9]
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    33,
    42,
    235,
    235,
    235,
    235,
    238,
    238,
    238,
    238,
    255,
    255,
    255,
    255,
    0,
    0,
    # preDetailsDelayMilliseconds
    5,
    # padding[49]
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
]


class Panel(IntEnum):
    UPLEFT = 0
    UP = 1
    UPRIGHT = 2
    LEFT = 3
    CENTER = 4
    RIGHT = 5
    DOWNLEFT = 6
    DOWN = 7
    DOWNRIGHT = 8


class Sensor(IntEnum):
    LEFT = 0
    RIGHT = 1
    UP = 2
    DOWN = 3


@bits(uint8_t, {"autolights": 0, "fsr": 1})
class FlagsType(BitsType): ...


@bits(uint16_t, {"steps": [0, 1, 2, 3, 4, 5, 6, 7, 8]})
class PanelMaskType(BitsType):
    def __getitem__(self, index: int) -> bool:
        # This lets us access the data with square brackets
        # ex. `config.PanelMaskType[Panel.UP]`
        return getattr(self, "steps", [])[index]

    def __setitem__(self, index: int, value: bool) -> None:
        # This lets us set the data with square brackets
        # ex. `config.PanelMaskType[Panel.DOWN] = True`
        steps = getattr(self, "steps", [])
        assert index <= len(steps)
        steps[index] = value


@struct_dataclass
class EnabledSensors(StructDataclass):
    # We can define the actual data we are ingesting here
    _raw: Annotated[list[uint8_t], TypeMeta(size=5)]

    # We use this to store the data in the way we actually want
    _data: list[list[bool]] = field(default_factory=list)

    def _decode(self, data: list[int]) -> None:
        # First call the super function to put the values in to _raw
        super()._decode(data)

        # Erase everything in self._data to remove any old data
        self._data = []

        # 2 Panels are packed into a single uint8_t, the left most 4 bits for the first
        # and the right most 4 bits for the second
        for bitlist in (list(map(bool, map(int, format(_byte, "#010b")[2:]))) for _byte in self._raw):
            self._data.append(bitlist[0:4])
            self._data.append(bitlist[4:])

        # Remove the last item in self._data as there are only 9 panels
        del self._data[-1]

    def _encode(self) -> list[int]:
        # Modify self._raw with updates values from self._data
        for idx, items in enumerate(list_chunks(self._data, 2)):
            # Last chunk
            if len(items) == 1:
                items.append([False, False, False, False])
            self._raw[idx] = sum(v << i for i, v in enumerate(list(itertools.chain.from_iterable(items))[::-1]))
        # Run the super function to return the data in self._raw()
        return super()._encode()

    def __getitem__(self, index: int) -> list[bool]:
        # This lets us access the data with square brackets
        # ex. `config.enabled_sensors[Panel.UP][Sensor.RIGHT]`
        return self._data[index]

    def __setitem__(self, index: int, value: list[bool]) -> None:
        # Only use this to set a complete set for a panel
        # ex. `config.enabled_sensors[Panel.UP] = [True, True, False, True]`
        if len(value) != 4 or not all(isinstance(x, bool) for x in value):
            raise Exception("use the right type of data scrub")
        self._data[index] = value


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


@struct_dataclass
class SMXConfigType(StructDataclass):
    master_version: uint8_t = 0xFF

    config_version: uint8_t = 0x05

    flags: FlagsType

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
