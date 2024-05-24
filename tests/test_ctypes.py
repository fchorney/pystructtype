from pystructtypes.structtypes import SMXConfig, TestClass


def test_smx_config():
    config = SMXConfig()

    input = [0x0F, 0xF0, 0xFF, 0xFF, 0xF0, 0xF0, 0x00, 0xF0, 0x0F, 0x0F, 0xF0, 0xFF, 0x00]

    config.decode(input, little_endian=True)

    assert config.a == [15, 240]

    e = config.encode(little_endian=True)

    assert e == input

def test_struct_dataclass():
    c = TestClass()
