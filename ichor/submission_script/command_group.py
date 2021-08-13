from typing import List, Optional, Tuple

from ichor.modules import Modules
from ichor.submission_script.command_line import CommandLine


class CommandGroup(CommandLine, list):
    """ Wraps around multiple jobs that are supposed to be ran as a job array.
    Since each job uses the same settings, we can just use the 0th index."""

    @property
    def command(self) -> str:
        return self[0].command

    @property
    def ncores(self) -> int:
        return self[0].ncores

    @property
    def data(self) -> Tuple[str]:
        return self[0].data

    @property
    def modules(self) -> Modules:
        return self[0].modules

    @property
    def arguments(self) -> List[str]:
        return self[0].arguments

    @property
    def options(self) -> List[str]:
        return self[0].options

    def repr(self, variables: Optional[List[str]] = None) -> str:
        return self[0].repr(variables)