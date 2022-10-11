import json
from pathlib import Path
from typing import List, Optional

from ichor.cli.general_menus.queue_menu import delete_jobs
from ichor.core.common.io import mkdir, pushd
from ichor.core.common.os import kill_pid, pid_exists
from ichor.core.daemon import Daemon
from ichor.hpc import FILE_STRUCTURE
from ichor.hpc.auto_run.standard_auto_run import rerun_from_failed
from ichor.hpc.auto_run.stop import stop


def find_child_processes_recursively(src: Path = Path.cwd()) -> List[Path]:
    child_processes = []

    cp_dir = None
    if (src / FILE_STRUCTURE["child_processes"]).exists():
        with open(src / FILE_STRUCTURE["child_processes"], "r") as f:
            child_processes += json.load(f)
    elif (src / FILE_STRUCTURE["atoms"]).exists():
        cp_dir = src / FILE_STRUCTURE["atoms"]
    elif (src / FILE_STRUCTURE["properties"]).exists():
        cp_dir = src / FILE_STRUCTURE["properties"]

    if cp_dir is not None:
        for d in cp_dir.iterdir():
            if d.is_dir() and (d / FILE_STRUCTURE["data"]).exists():
                child_processes += [d]
        child_processes = [str(cp.absolute()) for cp in child_processes]
        mkdir(src / FILE_STRUCTURE["child_processes"].parent)
        with open(src / FILE_STRUCTURE["child_processes"], "w") as f:
            json.dump(child_processes, f)

    for child_process in child_processes:
        child_processes += find_child_processes_recursively(
            Path(child_process)
        )

    child_processes = list(set(map(Path, child_processes)))
    return child_processes


def delete_child_process_jobs(
    child_processes: Optional[List[Path]] = None,
) -> None:
    from ichor.hpc import GLOBALS
    if child_processes is None:
        child_processes = find_child_processes_recursively()
    for child_process in child_processes:
        with GLOBALS.pushd(child_process):
            delete_jobs()
            stop()


class ReRunDaemon(Daemon):
    def __init__(self):
        from ichor.hpc import FILE_STRUCTURE, GLOBALS

        mkdir(FILE_STRUCTURE["rerun_daemon"])
        pidfile = GLOBALS.CWD / FILE_STRUCTURE["rerun_pid"]
        stdout = GLOBALS.CWD / FILE_STRUCTURE["rerun_stdout"]
        stderr = GLOBALS.CWD / FILE_STRUCTURE["rerun_stderr"]
        super().__init__(
            pidfile,
            stdout=stdout,
            stderr=stderr,
            pid_store=FILE_STRUCTURE["pids"],
        )

    def run(self):
        rerun_failed_child_process()
        self.stop()


def rerun_failed_child_process(
    child_processes: Optional[List[Path]] = None,
) -> None:
    from ichor.hpc import GLOBALS, Globals
    from ichor.hpc.arguments import Arguments

    if child_processes is None:
        child_processes = find_child_processes_recursively()
    for child_process in child_processes:
        # todo: ensure finished
        with GLOBALS.pushd(child_process):
            with Globals():
                GLOBALS.init_from_config(Arguments.config_file)
                rerun_from_failed()


def stop_all_child_processes(
    child_processes: Optional[List[Path]] = None,
) -> None:
    if child_processes is None:
        child_processes = find_child_processes_recursively()

    with open(FILE_STRUCTURE["pids"], "r") as f:
        for line in f:
            pid = int(line)
            if pid_exists(pid):
                kill_pid(pid)

    delete_child_process_jobs(child_processes)


def print_child_process_status(cpdir: Path):
    from ichor.core.common.io import pushd
    from ichor.hpc import FILE_STRUCTURE, GLOBALS
    from ichor.hpc.auto_run.counter import read_counter

    with GLOBALS.pushd(cpdir):
        path_status = f"{cpdir} Status"
        print("-" * len(path_status))
        print(path_status)
        print("-" * len(path_status))
        if FILE_STRUCTURE["counter"].exists():
            current_iteration, max_iteration = read_counter()
            print(f"Iteration {current_iteration} of {max_iteration}")
        else:
            print("No Counter File Found, Child Process May Have Finished")

        from ichor.core.common.io import last_modified
        from ichor.hpc.log import logger

        logger_path = Path(
            "ichor.log"
        ).absolute()  # <- better way to get this?
        print(f"{logger_path} last modified: {last_modified(logger_path)}")
        print()


def print_child_processes_status(child_processes: Optional[List[Path]] = None):
    child_processes = child_processes or find_child_processes_recursively()
    for cp in child_processes:
        print_child_process_status(cp)


def concat_dir_to_ts(child_processes: Optional[List[Path]] = None):
    from ichor.cli.general_menus.concatenate_points_menu import \
        concatenate_points_directories
    from ichor.core.analysis.get_path import get_dir
    from ichor.hpc import GLOBALS

    print("Enter PointsDirectory Location to concatenate to training sets: ")
    dir = get_dir().absolute()
    child_processes = child_processes or find_child_processes_recursively()

    for cp in child_processes:
        with GLOBALS.pushd(cp):
            ts = cp / FILE_STRUCTURE["training_set"]
            if ts.exists():
                concatenate_points_directories(ts, dir, verbose=True)
