from pathlib import Path
from typing import List, Optional, Tuple

from ichor.batch_system import BATCH_SYSTEM, JobID
from ichor.common.functools import classproperty
from ichor.common.io import mkdir
from ichor.common.uid import set_uid
from ichor.submission_script.command_group import CommandGroup
from ichor.submission_script.data_lock import DataLock


class SubmissionScript:
    """
    A class that can be used to construct submission scripts for various programs such as Gaussian and AIMALL.
    :param path: A path to a submission script (such as GAUSSIAN.sh and AIMALL.sh). These .sh files are submitted as jobs to CSF3/FFLUXLAB.
    """
    def __init__(self, path: Path):
        self.path = Path(path)
        self.commands = []  # a list of commands to be submitted to batch system

    @classproperty
    def filetype(self) -> str:
        """The extension of the submission script file. Will always be .sh (a shell script)"""
        return ".sh"

    def add_command(self, command):
        """Add a command to the list of commands."""
        self.commands += [command]

    @property
    def ncores(self) -> int:
        """Number of cores to be used for the job."""
        return max(command.ncores for command in self.grouped_commands)

    @property
    def default_options(self) -> List[str]:
        """ Returns a list of default options to use in a submission script for a job."""
        from ichor.globals import GLOBALS

        mkdir(GLOBALS.FILE_STRUCTURE["outputs"])
        mkdir(GLOBALS.FILE_STRUCTURE["errors"])

        # change current working directory to directory from which ICHOR is launched.
        # make the paths to outputs and errors absolute
        options = [
            BATCH_SYSTEM.change_working_directory(GLOBALS.CWD),
            BATCH_SYSTEM.output_directory(
                GLOBALS.FILE_STRUCTURE["outputs"].resolve()
            ),
            BATCH_SYSTEM.error_directory(
                GLOBALS.FILE_STRUCTURE["errors"].resolve()
            ),
        ]

        # if the number of cores is more than 1, have to add additional options
        if self.ncores > 1:
            options += [BATCH_SYSTEM.parallel_environment(self.ncores)]

        return options

    @property
    def options(self) -> List[str]:
        """Return the complete list of options (default options + other options for job)"""
        options = []
        for command in self.grouped_commands:
            options += command.options
        # do not duplicate commands
        return list(set(options + self.default_options))

    @property
    def modules(self) -> List[str]:
        """ Returns a list of modules that need to be loaded before a job can be ran. """
        from ichor.globals import GLOBALS

        modules = []
        for command in self.grouped_commands:
            modules += command.modules[GLOBALS.MACHINE]
        return list(set(modules))

    def group_commands(self) -> List[CommandGroup]:
        commands = []
        command_group = CommandGroup()  # make a new command group
        command_type = None
        # iterate over each command instance in self.commands
        # matt_todo: not really sure what this  is doing. Is this to make a group of Gaussian jobs for example to run in a job array?
        for command in self.commands:
            # if the command is not equal to command_type or commands.group is set to False (group method defined in CommandLine class, default True)
            if type(command) != command_type or not command.group:
                if len(command_group) > 0:  # just for first iteration of the loop
                    commands += [command_group]
                    command_group = CommandGroup()
                command_type = type(command)
            command_group += [command]
        # commands = [[GaussianCommand(), GaussianCommand()]]
        if len(command_group) > 0:
            commands += [command_group]
        return commands

        # ICHOR_SUBMIT_GJF
        # GAUSSIAN commands
        # ICHOR_SUBMIT_WFNS
        # AIMALL commands

    # matt_todo: why is a separate method needed? Make the top group_commands method into a property and rename it so there are not two methods
    @property
    def grouped_commands(self):
        return self.group_commands()

    @classproperty
    def separator(self):
        return ","

    @classproperty
    def datafile_var(self) -> str:
        return "ICHOR_DATFILE"

    @classmethod
    def arr(cls, n):
        return f"arr{n + 1}"

    @classmethod
    def array_index(cls, n):
        return f"${{{cls.arr(n)}[${BATCH_SYSTEM.TaskID}-1]}}"

    @classmethod
    def var(cls, n):
        return f"var{n + 1}"

    def write_datafile(self, datafile: Path, data: List[List[str]]) -> None:
        if not DataLock.locked:
            mkdir(datafile.parent)
            with open(datafile, "w") as f:
                for cmd_data in data:
                    f.write(f"{self.separator.join(map(str, cmd_data))}\n")

    def read_datafile_str(self, datafile: Path, data: List[List[str]]) -> str:
        ndata = len(data[0])

        datafile_str = f"{self.datafile_var}={datafile.absolute()}"

        read_datafile_str = "".join(
            f"{self.arr(i)}=()\n" for i in range(ndata)
        )
        read_datafile_str += (
            f"while IFS={self.separator} read -r "
            f"{' '.join(self.var(i) for i in range(ndata))}\n"
        )
        read_datafile_str += "do\n"
        for i in range(ndata):
            read_datafile_str += f"    {self.arr(i)}+=(${self.var(i)})\n"
        read_datafile_str += f"done < ${self.datafile_var}\n"

        return f"{datafile_str}\n{read_datafile_str}"

    def setup_datafile(
        self, datafile: Path, data: List[List[str]]
    ) -> Tuple[List[str], str]:
        self.write_datafile(datafile, data)
        datafile_str = self.read_datafile_str(datafile, data)
        datafile_variables = [self.array_index(i) for i in range(len(data[0]))]
        set_uid()
        return datafile_variables, datafile_str

    def write(self):
        from ichor.globals import GLOBALS

        mkdir(self.path.parent)

        with open(self.path, "w") as f:
            njobs = max(
                len(command_group) for command_group in self.grouped_commands
            )

            f.write("#!/bin/bash -l\n")
            for option in self.options:
                f.write(f"#{BATCH_SYSTEM.OptionCmd} {option}\n")
            if njobs > 1:
                f.write(
                    f"#{BATCH_SYSTEM.OptionCmd} {BATCH_SYSTEM.array_job(njobs)}\n"
                )
            else:
                f.write(f"{BATCH_SYSTEM.TaskID}=1\n")

            if self.ncores > 1:
                f.write(f"export OMP_NUM_THREADS={self.ncores}\n")
                f.write(f"export OMP_PROC_BIND=true\n")  # give physical cores

            for module in self.modules:
                f.write(f"module load {module}\n")

            for command_group in self.grouped_commands:
                command_variables = []
                if command_group.data: # Gaussian, Ferebus, AIMALL jobs
                    datafile = GLOBALS.FILE_STRUCTURE["datafiles"] / Path(
                        str(GLOBALS.UID)
                    )
                    command_group_data = [
                        command.data for command in command_group
                    ]
                    datafile_vars, datafile_str = self.setup_datafile(
                        datafile, command_group_data
                    )
                    command_variables += datafile_vars
                    f.write(f"{datafile_str}\n")
                f.write(f"{command_group.repr(command_variables)}\n")

    def submit(self, hold: Optional[JobID] = None) -> Optional[JobID]:
        from ichor.globals import GLOBALS

        if not GLOBALS.SUBMITTED:
            return BATCH_SYSTEM.submit_script(self.path, hold)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write()