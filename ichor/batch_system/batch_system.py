import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

from ichor.batch_system.node import NodeType
from ichor.common.functools import classproperty
from ichor.common.io import mkdir
from ichor.common.os import run_cmd


class JobID:
    """Class used to keep track of jobs submitted to compute nodes.

    :param script: A path to a script file such as GAUSSIAN.sh
    :param id: The job id given to the job when the job was submitted to a compute node.
    :instance: the unique identified (UUID) that is used for the job's datafile (containing the names of all the files needed for the job).
    """

    script: str
    id: str
    instance: str

    def __init__(
        self, script: Union[str, Path], id: str, instance: Optional[str] = None
    ):
        self.script = str(script)
        self.id = str(id)
        from ichor.globals import GLOBALS

        self.instance = instance or str(GLOBALS.UID)

    def write(self):
        from ichor.globals import GLOBALS

        mkdir(
            GLOBALS.FILE_STRUCTURE["jid"].parent
        )  # make parent directories if they don't exist

        job_ids = []
        # if the jid file exists (which contains queued jobs), then read it and append to job_ids list
        if GLOBALS.FILE_STRUCTURE["jid"].exists():
            with open(GLOBALS.FILE_STRUCTURE["jid"], "r") as f:
                try:
                    job_ids += json.load(f)
                except json.JSONDecodeError:
                    pass

        job_ids += [
            {
                "script": str(self.script),
                "id": str(self.id),
                "instance": str(self.instance),
            }
        ]

        # overwrite the jobs file, writing out any new jobs that were submitted plus the old jobs that were already in the file.
        with open(GLOBALS.FILE_STRUCTURE["jid"], "w") as f:
            json.dump(job_ids, f)

    def __repr__(self) -> str:
        return f"JobID(Script: {self.script}, Id: {self.id}, Instance: {self.instance})"


class BatchSystem(ABC):
    """An abstract base class for batch systems which are the systems used to submit jobs to compute nodes (for example Sun Grid Engine.)"""

    @staticmethod
    @abstractmethod
    def is_present() -> bool:
        pass

    @staticmethod
    @abstractmethod
    def current_node() -> NodeType:
        """Return the type of the node ichor is currently running on e.g. NodeType.ComputeNode"""
        pass

    @classmethod
    def submit_script(
        cls, job_script: Path, hold: Optional[Union[JobID, List[JobID]]] = None
    ) -> JobID:
        """Submit a job script to the batch system in order to queue/run jobs."""
        cmd = cls.submit_script_command
        if hold:
            cmd += cls.hold_job(hold)
        cmd += [job_script]

        stdout, stderr = run_cmd(
            cmd
        )  # this is the part which actually submits the job to  the queuing system
        job_id = JobID(
            job_script, cls.parse_job_id(stdout)
        )  # stdout is parsed because this is where the job id is printed once a job is submitted
        job_id.write()
        return job_id

    @classmethod
    def delete(cls, job: JobID):
        """Delete submitted jobs on the batch system."""
        cmd = cls.delete_job_command + [job.id]
        stdout, stderr = run_cmd(cmd)

    @classmethod
    @abstractmethod
    def parse_job_id(cls, stdout: str) -> str:
        pass

    @classmethod
    @abstractmethod
    def hold_job(cls, job: Union[JobID, List[JobID]]):
        """Hold a job in order for it to be ran at another time/ after another job has finished running."""
        pass

    @classproperty
    @abstractmethod
    def submit_script_command(self) -> List[str]:
        """Command to submit job to compute node, such as `qsub`."""
        pass

    @classmethod
    def delete_job(cls, job_id: JobID) -> None:
        """Delete job submitted to compute node."""
        cmd = [cls.delete_job_command, job_id]
        stdout, _ = run_cmd(cmd)
        return stdout

    @classproperty
    @abstractmethod
    def delete_job_command(self) -> List[str]:
        """Command that is used to delete a job, such as `qdel`."""
        pass

    @staticmethod
    @abstractmethod
    def status() -> str:
        """Returns the status of running jobs."""
        pass

    @classmethod
    @abstractmethod
    def change_working_directory(cls, path: Path) -> str:
        """ " Changes the working directory"""
        pass

    @classmethod
    @abstractmethod
    def output_directory(cls, path: Path) -> str:
        """Changes the output directory where (these are .o files)"""
        pass

    @classmethod
    @abstractmethod
    def error_directory(cls, path: Path) -> str:
        """Changes the error directory where (these are .e files)"""
        pass

    @classmethod
    @abstractmethod
    def parallel_environment(cls, ncores: int) -> str:
        """Returns the flag to set the parallel environment for the job"""
        pass

    @classmethod
    @abstractmethod
    def array_job(cls, njobs: int) -> str:
        """Returns the flag to set the number of tasks for a job"""
        pass

    @classproperty
    @abstractmethod
    def JobID(self) -> str:
        """Returns environment variable name to get the current job id, not currently used"""
        pass

    @classproperty
    @abstractmethod
    def TaskID(self) -> str:
        """Returns environment variable name for the current task id, used to index datafile arrays and by CheckManager"""
        pass

    @classproperty
    @abstractmethod
    def TaskLast(self) -> str:
        """Returns environment variable name for the last task in a task array, used by CheckManager"""
        pass

    @classproperty
    @abstractmethod
    def NumProcs(self) -> str:
        """Returns environment variable name for the number of processors assigned to a job, used to set OpenMP etc."""
        pass

    @classproperty
    @abstractmethod
    def OptionCmd(self) -> str:
        """Returns the character used to define a batch system option statement in a submission script"""
        pass
