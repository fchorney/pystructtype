from test.examples import TEST_CONFIG_DATA, SMXConfigType


def test_example_builds() -> None:
    s = SMXConfigType()
    s.decode(TEST_CONFIG_DATA, little_endian=True)

    assert s
    assert s._to_list(s.encode(little_endian=True)) == TEST_CONFIG_DATA
