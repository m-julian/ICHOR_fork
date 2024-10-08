import json
from enum import Enum
from pathlib import Path
from typing import Optional

from ichor.core.atoms import Atom, Atoms
from ichor.core.files.file import FileContents, ReadFile, WriteFile
from ichor.core.files.file_data import HasAtoms


class PandoraCCSDmod(Enum):
    CCSD = "ccsd"
    CCSD_HF = "ccsdHF"
    CCSD_MULLER = "ccsdM"


class PandoraInput(HasAtoms, ReadFile, WriteFile):

    _filetype = ".pandora"

    def __init__(
        self,
        path: Path,
        atoms: Optional[Atoms] = None,
        ccsdmod: PandoraCCSDmod = FileContents,
        morfi_grid_radial: float = FileContents,
        morfi_grid_angular: int = FileContents,
        morfi_grid_radial_h: float = FileContents,
        morfi_grid_angular_h: int = FileContents,
        method: str = FileContents,
        basis_set: str = FileContents,
    ):
        super(ReadFile, self).__init__(path)

        self.atoms = atoms
        self.ccsdmod: PandoraCCSDmod = ccsdmod
        self.morfi_grid_radial: float = morfi_grid_radial
        self.morfi_grid_angular: int = morfi_grid_angular
        self.morfi_grid_radial_h: float = morfi_grid_radial_h
        self.morfi_grid_angular_h: int = morfi_grid_angular_h
        self.method = method
        self.basis_set = basis_set

    def _read_file(self):
        with open(self.path, "r") as f:
            data = json.load(f)
        self.atoms = Atoms()
        for atom in data["system"]["geometry"]:
            self.atoms.add(Atom(atom[0], atom[1], atom[2], atom[3]))
        self.ccsdmod = PandoraCCSDmod(data["pandora"]["ccsdmod"])
        self.basis_set = data["pyscf"]["method"]
        self.basis_set = data["pyscf"]["basis"]
        self.morfi_grid_angular = data["morfi"]["grid"]["angular"]
        self.morfi_grid_radial = data["morfi"]["grid"]["radial"]
        self.morfi_grid_angular_h = data["morfi"]["grid"]["angular_h"]
        self.morfi_grid_radial_h = data["morfi"]["grid"]["radial_h"]

    def _set_write_defaults_if_needed(self):
        self.atoms.centre()
        # todo: ensure no atoms are at the origin (wihtin 1e-6) as this will break morfi

        if not self.basis_set.startswith("unc-"):
            self.basis_set = f"unc-{self.basis_set}"

    def _write_file(self, path: Path, system_name: str):

        data = {
            "system": {
                "name": system_name.lower(),
                "geometry": [
                    [atom.type, atom.x, atom.y, atom.z] for atom in self.atoms
                ],
            },
            "pandora": {
                "ccsdmod": self.ccsdmod.value,
            },
            "pyscf": {
                "method": self.method,
                "basis": self.basis_set,
            },
            "morfi": {
                "grid": {
                    "radial": self.morfi_grid_radial,
                    "angular": self.morfi_grid_angular,
                    "radial_h": self.morfi_grid_radial_h,
                    "angular_h": self.morfi_grid_angular_h,
                },
            },
        }

        write_str = json.dumps(data, indent=4)
        return write_str
