from typing import Annotated, Any, Generator, get_args, get_origin


def list_chunks(_list: list, chunk_size: int) -> Generator[list, None, None]:
    for i in range(0, len(_list), chunk_size):
        yield _list[i : i + chunk_size]


def type_from_annotation(_type: type):
    if (origin := get_origin(_type)) and origin is Annotated:
        arg = None
        t: Any = _type
        while t := get_args(t):
            arg = t[0]
        return arg
    return _type
