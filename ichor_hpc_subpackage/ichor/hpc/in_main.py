""" This is used to check if ichor is launched as command line interface (CLI) or used as a library. If ichor3.py is the file that is being ran, then ICHOR is ran as CLI, so the class Arguments needs to be used. If ichor is used
as a library, then the Arguments class is not used. This is needed to prevent cyclic imports or settings overwriting that Arguments does."""

from functools import wraps
from typing import Any

from ichor.core.common.types.itypes import F

_IN_MAIN = False


def main_only(f: F) -> F:
    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        if _IN_MAIN:
            return f(*args, **kwargs)

    return wrapper
