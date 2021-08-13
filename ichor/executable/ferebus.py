from ichor.executable.executable import Executable
from ichor.common.io import pushd, mkdir


class Ferebus(Executable):
    def __init__(self):
        Executable.__init__(self, git_repository="https://github.com/popelier-group/FEREBUS")

    @property
    def exepath(self):
        return self.path / "build" / "ferebus"

    def build(self):
        with pushd(self.path):

            # mkdir("build")
            # with pushd("build"):
