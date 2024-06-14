from enum import IntEnum

from pystructtypes.structtypes import SMXConfigType


# fmt: off
config_data = [
    # masterVersion
    5,
    # configVersion
    5,
    # flags
    3,
    # debounceNodelayMilliseconds
    15, 0,
    # debounceDelayMilliseconds
    0, 0,
    # panelDebounceMicroseconds
    160, 15,
    # autoCalibrationMaxDeviation
    100,
    # badSensorMinimumDelaySeconds
    15,
    # autoCalibrationAveragesPerUpdate
    44, 1,
    # autoCalibrationSamplesPerAverage
    100, 0,
    # autoCalibrationMaxTare
    255, 255,
    # enabledSensors[5]
    15, 15, 15, 15, 0,
    # autoLightsTimeout
    7,
    # stepColor[3 * 9]
    170, 170, 170,
    170, 170, 170,
    170, 170, 170,
    170, 170, 170,
    170, 170, 170,
    170, 170, 170,
    170, 170, 170,
    170, 170, 170,
    170, 170, 170,
    # platformStripColor[3]
    0, 72, 143,
    # autoLightPanelMask
    170, 0,
    # panelRotation
    0,
    # panelSettings[9]
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    33, 42, 235, 235, 235, 235, 238, 238, 238, 238, 255, 255, 255, 255, 0, 0,
    # preDetailsDelayMilliseconds
    5,
    # padding[49]
    255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255,
]
# fmt: on


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


def test_smx_config():
    c = SMXConfigType()

    c.decode(config_data, little_endian=True)

    # c.enabled_sensors[Panel.UP][Sensor.RIGHT] = False
    # c.flags.autolights = False
    # c.auto_light_panel_mask[Panel.UPLEFT] = True

    e = c.encode(little_endian=True)

    assert c._to_list(e) == config_data
