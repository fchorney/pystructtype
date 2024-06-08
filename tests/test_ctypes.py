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


def test_smx_config():
    c = SMXConfigType()

    c.decode(config_data, little_endian=True)

    e = c.encode(little_endian=True)

    assert c._to_list(e) == config_data
