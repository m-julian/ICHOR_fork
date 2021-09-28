import sys
from pathlib import Path
from typing import Optional, List

from ichor.batch_system import JobID
from ichor.common.io import last_line
from ichor.files import PointsDirectory, GJF
from ichor.logging import logger
from ichor.submission_script import (SCRIPT_NAMES, GaussianCommand,
                                     SubmissionScript, print_completed)


def submit_points_directory_to_gaussian(directory: Path) -> Optional[JobID]:
    """Function that submits all .gjf files in a directory to Gaussian, which will output .wfn files.

    :param directory: A Path object which is the path of the directory (commonly traning set path, sample pool path, etc.).
    """
    points = PointsDirectory(
        directory
    )  # a directory which contains points (a bunch of molecular geometries)
    gjf_files = write_gjfs(points)
    return submit_gjfs(gjf_files)


def submit_gjfs(gjfs: List[Path], force: bool = False, hold: Optional[JobID] = None) -> Optional[JobID]:
    # make a SubmissionScript instance which is going to house all the jobs that are going to be ran
    with SubmissionScript(SCRIPT_NAMES["gaussian"]) as submission_script:
        for gjf in gjfs:
            if force or not gjf.with_suffix('.wfn').exists():
                submission_script.add_command(GaussianCommand(gjf))
                logger.debug(
                    f"Adding {gjf} to {submission_script.path}"
                )  # make a list of GaussianCommand instances.
    # write the final submission script file that containing the job that needs to be ran (could be an array job that has many tasks)
    if len(submission_script.commands) > 0:
        logger.info(
            f"Submitting {len(submission_script.commands)} GJF(s) to Gaussian"
        )
        # submit the final submission script to the queuing system, so that job is ran on compute nodes.
        return submission_script.submit(hold=hold)


def write_gjfs(points: PointsDirectory) -> List[Path]:
    gjfs = []
    for point in points:
        if not point.gjf.exists():
            point.gjf = GJF(Path(point.path / (point.path.name + GJF.filetype)))
            point.gjf.atoms = point.xyz
        point.gjf.write()
        gjfs.append(point.gjf.path)
    return gjfs


def check_gaussian_output(gaussian_file: str):
    """Checks if Gaussian jobs ran correctly and a full .wfn file is returned. If there is no .wfn file or it does not
    have the correct contents, then rerun Gaussian."""
    if not gaussian_file:
        print_completed()
        sys.exit()
    if Path(gaussian_file).with_suffix(
        ".wfn"
    ).exists() and "TOTAL ENERGY" in last_line(
        Path(gaussian_file).with_suffix(".wfn")
    ):
        print_completed()
    else:
        logger.error(f"Gaussian Job {gaussian_file} failed to run")