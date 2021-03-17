import ast
from functools import wraps
from typing import Any, List, Union, cast

from ichor.common.types import Version
from ichor.common.types.bool import check_bool
from ichor.globals.formatters import cleanup_str
from ichor.typing import F


def parser(func: F) -> F:
    @wraps(func)
    def wrapper(val: Any) -> Any:
        if val is None:
            return val
        else:
            return func(val)

    return cast(F, wrapper)


@parser
def split_keywords(keywords: Union[str, List[str]]):
    if isinstance(keywords, str):
        keywords = keywords.replace("[", "")
        keywords = keywords.replace("]", "")
        keywords = keywords.split(",") if "," in keywords else keywords.split()
    return [cleanup_str(keyword) for keyword in keywords]


@parser
def read_alf(alf: Union[str, List[List[int]]]):
    if isinstance(alf, str):
        alf = ast.literal_eval(alf)
    if isinstance(alf, list):
        alf = [[int(i) for i in j] for j in alf]
    return alf


@parser
def read_version(ver: str) -> Version:
    return Version(ver)


@parser
def parse_str(inp: Any) -> str:
    return str(inp)


@parser
def parse_bool(inp: Any) -> bool:
    return check_bool(inp)


@parser
def parse_int(inp: Any) -> int:
    return int(inp)


@parser
def parse_float(inp: Any) -> float:
    return float(inp)
