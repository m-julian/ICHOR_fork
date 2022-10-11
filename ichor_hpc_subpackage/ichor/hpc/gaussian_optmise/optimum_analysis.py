from pathlib import Path
from typing import Optional

from ichor.core.common.io import get_files_of_type
from ichor.core.files import WFN


class UnknownOptimumEnergyFileType(Exception):
    pass

def get_wfn_energy_from_dir(d: Path) -> Optional[float]:
    wfns = get_files_of_type(WFN.filetype, d)
    if len(wfns) > 0:
        return WFN(wfns[0]).energy

def get_wfn_energy_from_file(wfn_file: Path) -> Optional[float]:
    """
    Tries to find the optimum energy for the current system
    :return: ether the optimum energy or None if the optimum energy cannot be found
    """

    if wfn_file.exists():
        wfn_energy = WFN(wfn_file).energy
        if wfn_energy:
            return wfn_energy
