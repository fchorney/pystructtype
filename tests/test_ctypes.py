from pystructtypes.structtypes import Gotem, SMXConfig_T, TestClass2


# def test_smx_config():
#     config = SMXConfig()
#
#     _input = [
#         0x0F,
#         0xF0,
#         0xFF,
#         0xFF,
#         0xF0,
#         0xF0,
#         0x00,
#         0xF0,
#         0x0F,
#         0x0F,
#         0xF0,
#         0xFF,
#         0x00,
#     ]
#
#     config.decode(_input, little_endian=True)
#
#     assert config.a == [15, 240]
#
#     e = config.encode(little_endian=True)
#
#     assert e == _input


def test_struct_dataclass():
    c = TestClass2()

    assert isinstance(c, TestClass2)

    _input = [
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x10,
        0x11,
        0x12,
        0x13,
        0x14,
        0x15,
        0x16,
        0x17,
    ]
    c.decode(_input, little_endian=True)
    e = c._to_list(c.encode(little_endian=True))
    assert e == _input


def test_smx_config():
    c = SMXConfig_T()

    assert isinstance(c, SMXConfig_T)


def test_gotem():
    c = Gotem()

    assert isinstance(c, Gotem)
