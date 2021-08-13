import os
import re
from pathlib import Path
from typing import List

from ichor.batch_system.batch_system import BatchSystem, JobID
from ichor.common.functools import classproperty
from ichor.common.io import convert_to_path # matt_todo: Import not used here


class SunGridEngine(BatchSystem):
    """ A class that implements methods ICHOR uses to submit jobs to the Sun Grid Engine (SGE) batch system. These methods/properties
    are used to construct job scripts for any program we want to run on SGE. """
    @staticmethod
    def is_present() -> bool:
        """ Check if SGE is present on the current machine ICHOR is running on."""
        return "SGE_ROOT" in os.environ.keys()

    @classproperty
    def submit_script_command(self) -> List[str]:
        """ Return a list containing command used to submit jobs to SGE batch system."""
        return ["qsub"]

    @classmethod
    def parse_job_id(cls, stdout) -> str:
        return re.findall(r"\d+", stdout)[0]

    @classmethod
    def hold_job(cls, job_id: JobID) -> List[str]:
        """ Return a list containing `hold_jid` keyword and job id which is used to hold a particular job id for it to be ran at a later time. """
        return ["-hold_jid", f"{job_id.id}"]

    @classproperty
    def delete_job_command(self) -> List[str]:
        """ Return a list containing command used to delete jobs on SGE batch system. """
        return ["qdel"]

    @staticmethod
    def status() -> List[str]:
        return ["qstat"]

    @classmethod
    def change_working_directory(cls, path: Path) -> str:
        """ Return the line in the job script definning the working directory from where the job is going to run. """
        return f"-wd {path}"

    @classmethod
    def output_directory(cls, path: Path) -> str:
        """ Return the line in the job script defining the output directory where the output of the job should be written to.
        These files end in `.o{job_id}`. """
        return f"-o {path}"

    @classmethod
    def error_directory(cls, path: Path) -> str:
        """ Return the line in the job script defining the error directory where any errors from the job should be written to.
        These files end in `.e{job_id}`. """
        return f"-e {path}"

    @classmethod
    def parallel_environment(cls, ncores: int) -> str:
        """ Returns the line in the job script defining the number of corest to be used for the job. """
        from ichor.batch_system import PARALLEL_ENVIRONMENT
        from ichor.globals import GLOBALS

        return f"-pe {PARALLEL_ENVIRONMENT[GLOBALS.MACHINE][ncores]} {ncores}"

    @classmethod
    def array_job(cls, njobs: int) -> str:
        """ Returns the line in the job script that specifies this job is an array job. These jobs are run at the same time in parallel
        as they do not depend on one another. An example will be running 50 Gaussian or AIMALL jobs at the same time without having to submit
        50 separate jobs. Instead 1 array job can be submitted. """
        return f"-t 1-{njobs}"

    @classproperty
    def JobID(self) -> str:
        return "JOB_ID"

    @classproperty
    def TaskID(self) -> str:
        return "SGE_TASK_ID"

    @classproperty
    def TaskLast(self) -> str:
        return "SGE_TASK_LAST"

    @classproperty
    def NumProcs(self) -> str:
        return "NSLOTS"

    @classproperty
    def OptionCmd(self) -> str:
        return "$"