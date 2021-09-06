from ichor.common.types import RangeDict
from ichor.globals import Machine


class ParallelEnvironment(RangeDict):
    """A dictionary containing key:value pairs in which the key is a keyword used by the submission system to specify
    the number of cores and the value is a tuple containing a lower and upper bound for the number of cores. Once"""

    def __getitem__(self, item: int) -> str:
        try:
            return super().__getitem__(item)
        except KeyError:
            if item == 1:
                return ""
            raise KeyError(f"'ParallelEnvironment' for {item} cores not found")


class ParallelEnvironments(dict):
    """A wrapper around multiple parallel environments. Essentially a dictionary whose values are `ParallelEnvironemnt` instances. This is used to
    get the specific keyword different machines (CSF3/FFLUXLAB,etc.) use for jobs running on multiple cores."""

    def __getitem__(self, item: Machine) -> ParallelEnvironment:
        if item not in self.keys():
            self[item] = ParallelEnvironment()
        return super().__getitem__(item)
