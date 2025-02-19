from collections.abc import Generator


def list_chunks(_list: list, n: int) -> Generator[list]:
    """
    Yield successive n-sized chunks from a list.
    :param _list: List to chunk out
    :param n: Size of chunks
    :return: Generator of n-sized chunks of _list
    """
    yield from (_list[i : i + n] for i in range(0, len(_list), n))


def int_to_bool_list(data: int | list[int], byte_length: int) -> list[bool]:
    """
    Converts an integer or a list of integers into a list of bools representing the bits

    ex. ord("A") or 0b01000001 = [False, True, False, False, False, False, False, True]

    ex. [ord("A"), ord("B")] = [False, True, False, False, False, False, False, True,
    False, True, False, False, False, False, True, False]

    :param data: Integer(s) to be converted
    :param byte_length: Number of bytes to extract from integer(s)
    :return: List of bools representing each bit in the data
    """
    # Convert a single int into a list, so we can assume we're always working with a list here
    data = [data] if isinstance(data, int) else data

    # The amount of bits we end up with will be the number of bytes we expect in the int times 8 (8 bits in a byte)
    # For example uint8_t would have 1 byte, but uint16_t would have 2 bytes
    byte_size = (byte_length * 8) // len(data)

    bit_strs = []
    for val in data:
        # Convert the int(s) in to a string of bits (add 2 to account for the `0b` prefix)
        tmp_str = format(val, f"#0{byte_size + 2}b")
        # Cut off the `0b` prefix of the bit string, and reverse it
        bit_strs.append(tmp_str.removeprefix("0b")[::-1])
    # Convert the bit_str to a list of ints representing single bits
    bit_list = map(int, "".join(bit_strs[::-1]))
    # Convert the bit list to bools and return
    return list(map(bool, bit_list))
