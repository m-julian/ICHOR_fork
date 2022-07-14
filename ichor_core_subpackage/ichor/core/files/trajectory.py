import ast
import re
from pathlib import Path
from typing import Iterable, List, Optional, Union

import numpy as np
from ichor.core.atoms import Atom, Atoms, ListOfAtoms
from ichor.core.common.functools import classproperty
from ichor.core.common.io import mkdir
from ichor.core.files.file import File, FileState, ReadFile, WriteFile


def spherical_to_cartesian(r, theta, phi) -> List[float]:
    """
    Spherical to cartesian transformation, where r ∈ [0, ∞), θ ∈ [0, π], φ ∈ [-π, π).
        x = rsinθcosϕ
        y = rsinθsinϕ
        z = rcosθ
    """
    x = r * np.sin(theta) * np.cos(phi)
    y = r * np.sin(phi) * np.sin(theta)
    z = r * np.cos(theta)
    return [x, y, z]


def features_to_coordinates(features: np.ndarray) -> np.ndarray:
    """Converts a given n_points x n_features matrix of features to cartesian coordinates of shape
    n_points x n_atoms x 3

    :param features: a numpy array of shape n_points x n_features
    """

    if features.ndim == 1:
        features = np.expand_dims(features, axis=0)

    all_points = []  # 3d array
    one_point = []  # 2d array

    for row in features:  # iterate over rows, which are individual points

        # origin and x-axis and xy-plane atoms
        one_point.append([0, 0, 0])
        one_point.append([row[0], 0, 0])
        one_point.append(
            spherical_to_cartesian(row[1], np.pi / 2, row[2])
        )  # theta is always pi/2 because it is in the xy plane

        # all other atoms
        for i in range(3, features.shape[-1], 3):
            r = row[i]
            theta = row[i + 1]
            phi = row[i + 2]
            one_point.append(spherical_to_cartesian(r, theta, phi))

        all_points.append(one_point)
        one_point = []

    return np.array(all_points)


class Trajectory(ListOfAtoms, ReadFile, WriteFile, File):
    """Handles .xyz files that have multiple timesteps, with each timestep giving the x y z coordinates of the
    atoms. A user can also initialize an empty trajectory and append `Atoms` instances to it without reading in a .xyz file. This allows
    the user to build custom trajectories containing any sort of geometries.

    :param path: The path to a .xyz file that contains timesteps. Set to None by default as the user can initialize an empty trajectory and built it up
        themselves
    """

    def __init__(self, path: Union[Path, str] = None):
        ListOfAtoms.__init__(self)
        File.__init__(self, path)

    def _read_file(self):
        with open(self.path, "r") as f:
            # make empty Atoms instance in which to store one timestep
            atoms = Atoms()
            for line in f:
                # match the line containing the number of atoms in timestep
                if re.match(r"^\s*\d+$", line):
                    natoms = int(line)
                    # this is the comment line of xyz files. It can be empty or contain some useful information that can be stored.
                    line = next(f)
                    # if the comment line properties errors, we can store these
                    if re.match(
                        r"^\s*?i\s*?=\s*?\d+\s*properties_error", line
                    ):
                        properties_error = line.split("=")[-1].strip()
                        atoms.properties_error = ast.literal_eval(
                            properties_error
                        )
                    # the next line after the comment line is where coordinates begin
                    for _ in range(natoms):
                        line = next(f)
                        if re.match(
                            r"^\s*?\w+(\s+[+-]?\d+.\d+([Ee]?[+-]?\d+)?){3}",
                            line,
                        ):
                            # add *_ to work for extended xyz which contain extra information after x,y,z coordinates
                            atom_type, x, y, z, *_ = line.split()
                            atoms.add(
                                Atom(atom_type, float(x), float(y), float(z))
                            )

                    # add the Atoms instance to the Trajectory instance
                    self.add(atoms)
                    # make new Atoms instance where next timestep can be stored
                    atoms = Atoms()

    @classproperty
    def filetype(self) -> str:
        return ".xyz"

    def add(self, atoms):
        """Add a list of Atoms (corresponding to one timestep) to the end of the trajectory list"""
        if isinstance(atoms, Atoms):
            self.append(atoms)
        else:
            raise ValueError(
                f"Cannot add an instance of {type(atoms)} to self."
            )

    def rmsd(self, ref=None):
        if ref is None:
            ref = self[0]
        elif isinstance(ref, int):
            ref = self[ref]

        return [ref.rmsd(point) for point in self]

    def to_dir(self, system_name: str, root: Path, every: int = 1):
        """Writes out every nth timestep to a separate .xyz file to a given directory

        :param system_name: The name of the
        :param root: A Path to a directory where to write the .xyz files. An empty directory is made for the given Path and
            overwrites an existing directory for the given Path.
        :param every: An integer value that indicates the nth step at which an xyz file should be written. Default is 1. If
            a value eg. 5 is given, then it will only write out a .xyz file for every 5th timestep.
        """
        from ichor.core.files import XYZ

        mkdir(root, empty=True)
        for i, geometry in enumerate(self):

            if (i % every) == 0:

                path = Path(system_name + str(i + 1) + ".xyz")
                path = root / path
                xyz_file = XYZ(path, geometry)
                xyz_file.write()

    @classmethod
    def features_file_to_trajectory(
        cls,
        f: "Path",
        atom_types: List[str],
        header=0,
        index_col=0,
        sheet_name=0,
    ) -> "Trajectory":

        """Takes in a csv or excel file containing features and convert it to a `Trajectory` object.
        It assumes that the features start from the first column (column after the index column, if one exists). Feature files that
        are written out by ichor are in Bohr instead of Angstroms for now. After converting to cartesian coordinates, we have to convert
        Bohr to Angstroms because .xyz files are written out in Angstroms (and programs like Avogadro, VMD, etc. expect distances in angstroms).
        Failing to do that will result in xyz files that are in Bohr, so if features are calculated from them again, the features will be wrong.

        :param f: Path to the file (either .csv or .xlsx) containing the features. We only need the features for one atom to reconstruct the geometries,
            thus we only need 1 csv file or 1 sheet of an excel file. By default, the 0th sheet of the excel file is read in.
        :param atom_types: A list of strings corresponding to the atom elements (C, O, H, etc.). This has to be ordered the same way
            as atoms corresponding to the features.
        :param header: Whether the first line of the csv file contains the names of the columns. Default is set to 0 to use the 0th row.
        :param index_col: Whether a column should be used as the index column. Default is set to 0 to use 0th column.
        :param sheet_name: The excel sheet to be used to convert to xyz. Default is 0. This is only needed for excel files, not csv files.
        """

        from pathlib import Path

        import pandas as pd
        from ichor.core.constants import bohr2ang

        if isinstance(f, str):
            f = Path(f)
        if f.suffix == ".xlsx":
            features_array = pd.read_excel(
                f, sheet_name=sheet_name, header=header, index_col=index_col
            ).values
        elif f.suffix == ".csv":
            features_array = pd.read_csv(
                f, header=header, index_col=index_col
            ).values
        else:
            raise NotImplementedError(
                "File needs to have .xlsx or .csv extension"
            )

        n_features = 3 * len(atom_types) - 6

        features_array = features_array[:, :n_features]

        # xyz coordinates are currently in bohr, so convert them to angstroms
        xyz_array = features_to_coordinates(features_array)
        xyz_array = bohr2ang * xyz_array

        trajectory = Trajectory()

        for geometry in xyz_array:
            # initialize empty Atoms instance
            atoms = Atoms()
            for ty, atom_coord in zip(atom_types, geometry):
                # add Atom instances for every atom in the geometry to the Atoms instance
                atoms.add(
                    Atom(ty, atom_coord[0], atom_coord[1], atom_coord[2])
                )
            # Add the filled Atoms instance to the Trajectory instance and repeat for next geometry
            trajectory.add(atoms)

        return trajectory

    def _write_file(self, path: Path, every: int = 1):
        with open(path, "w") as f:
            n = 0
            for i, frame in enumerate(self):
                n += 1
                if n == every:
                    f.write(f"{len(frame)}\n")
                    f.write(f"i = {i}\n")
                    for atom in frame:
                        f.write(
                            f"{atom.type} {atom.x:16.8f} {atom.y:16.8f} {atom.z:16.8f}\n"
                        )
                    n = 0

    def __getitem__(self, item) -> Atoms:
        """Used to index a Trajectory instance by a str (eg. trajectory['C1']) or by integer (eg. trajectory[2]),
        remember that indeces in Python start at 0, so trajectory[2] is the 3rd timestep.
        You can use something like (np.array([traj[i].features for i in range(2)]).shape) to features of a slice of
        a trajectory as slice is not implemented in __getitem__"""
        if self.state is not FileState.Read:
            self.read()
        return super().__getitem__(item)

    def __iter__(self) -> Iterable[Atoms]:
        """Used to iterate over timesteps (Atoms instances) in places such as for loops"""
        if self.state is not FileState.Read:
            self.read()
        return super().__iter__()

    def __len__(self):
        """Returns the number of timesteps in the Trajectory instance"""
        if self.state is not FileState.Read:
            self.read()
        return super().__len__()

    def __repr__(self) -> str:
        """Make a repr otherwise doing print(trajectory_instance) will print out an empty list if the trajectory attributes have not been accessed yet,
        due to how how the files are being parsed using PathObject/File classes."""
        return (
            f"class {self.__class__}\n"
            f"xyz_file: {self.path or None}\n"
            f"atom_names: {self.atom_names}\n"
            f"trajectory_coordinates_shape (n_timesteps, n_atoms, 3): {self.coordinates.shape}\n"
        )
