"""Per-atom auto run and per-property auto run. Each atom gets its own training set."""

from ichor.auto_run.per.child_processes import (
    ReRunDaemon,
    delete_child_process_jobs,
    find_child_processes_recursively,
    rerun_failed_child_process,
    stop_all_child_processes,
)
from ichor.auto_run.per.per_atom import (
    PerAtomDaemon,
    auto_run_per_atom,
    make_missing_atom_models,
    make_models_atoms_menu,
    run_per_atom_daemon,
)
from ichor.auto_run.per.per_atom_per_property import (
    PerAtomPerPropertyDaemon,
    auto_run_per_atom_per_property,
    run_per_atom_per_property_daemon,
)
from ichor.auto_run.per.per_property import (
    PerPropertyDaemon,
    auto_run_per_property,
    run_per_property_daemon,
)

__all__ = [
    "auto_run_per_atom",
    "PerAtomDaemon",
    "run_per_atom_daemon",
    "auto_run_per_property",
    "PerPropertyDaemon",
    "auto_run_per_atom_per_property",
    "PerAtomPerPropertyDaemon",
    "run_per_atom_per_property_daemon",
    "find_child_processes_recursively",
    "delete_child_process_jobs",
    "rerun_failed_child_process",
    "run_per_property_daemon",
    "ReRunDaemon",
    "stop_all_child_processes",
    "make_missing_atom_models",
    "make_models_atoms_menu",
]
