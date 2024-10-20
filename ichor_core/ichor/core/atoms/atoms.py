import itertools as it
from itertools import compress
from typing import Callable, Dict, List, Optional, Sequence, Union

import numpy as np
from ichor.core.atoms.alf import ALF
from ichor.core.atoms.atom import Atom


class Atoms(list):
    """
    The Atoms class handles ONE timestep in the trajectory. It is mainly used to group together
    Atom objects that are in the same timestep. However, it is written in a way that any
    number of Atom instances can be grouped together if the user wants to do so.

    e.g. if we have a trajectory of methanol (6 atoms) with 1000 timesteps, we will have 1000 Atoms instances. Each
    of the Atoms instances will hold 6 instances of the Atom class.
    """

    def __init__(self, atoms: Optional[Sequence[Atom]] = None):
        super().__init__()
        self._centred = False
        self._counter = it.count(1)
        if atoms is not None:
            for atom in atoms:
                self.add(atom)

    def add(self, atom: Atom):
        """
        Add Atom instances for each atom in the timestep to the self._atoms list.
        Each coordinate line in the trajectory file (for one timestep) is added as a separate Atom instance.
        """
        self.append(atom)

    def append(self, atom: Atom):
        """Appends an `Atom` instance to self."""
        atom.parent = self
        if atom._index is None:
            atom.index = next(self._counter)
        super().append(atom)

    def copy(self) -> "Atoms":
        """Creates a new atoms instance (different object) from the current `Atoms` instance."""
        new = Atoms()
        for a in self:
            new.add(Atom.from_atom(a))
        return new

    def to_angstroms(self) -> "Atoms":
        """
        Convert the x, y, z coordinates of all Atom instances held in an Atoms instance to angstroms
        """
        return Atoms([atom.to_angstroms() for atom in self])

    def to_bohr(self) -> "Atoms":
        """
        Convert the x, y, z coordinates of all Atom instances held in an Atoms instance to bohr
        """
        return Atoms([atom.to_bohr() for atom in self])

    @property
    def nuclear_charge_sum(self) -> int:
        """Returns the sum of nuclear charges of `Atoms` instance"""
        return sum(atom.nuclear_charge for atom in self)

    @property
    def natoms(self) -> int:
        """
        Returns the number of atoms in a timestep. Since each timestep has the same number of atoms. This
        means the number of atoms in the system is returned.
        """
        return len(self)

    @property
    def names(self) -> List[str]:
        """Return a list of atom names that are held in the instance of Atoms."""

        return self.atom_names

    @property
    def types(self) -> List[str]:
        """Returns the atom elements for atoms, removes duplicates"""
        return list({atom.type for atom in self})

    @property
    def types_extended(self) -> list:
        """Returns the atom elements for all atoms, includes duplicates."""
        return [atom.type for atom in self]

    @property
    def coordinates(self) -> np.ndarray:
        """Returns an array that contains the coordinates for each Atom instance held in the Atoms instance."""
        return np.array([atom.coordinates for atom in self])

    @property
    def centroid(self) -> np.ndarray:
        """Returns the centroid of the system (the mean of the x,y,z coordinates of the atoms)."""
        coordinates = self.coordinates.T

        x = np.mean(coordinates[0])
        y = np.mean(coordinates[1])
        z = np.mean(coordinates[2])

        return np.array([x, y, z])

    @property
    def masses(self) -> List[float]:
        """Returns a list of the masses of the Atom instances held in the Atoms instance."""
        return [atom.mass for atom in self]

    @property
    def atom_names(self) -> List[str]:
        """Returns the atom names as a list (['O1', 'H2'...])."""
        return [atom.name for atom in self]

    @property
    def xyz_string(self):
        """Returns a string containing all atoms and their coordinates stored in the Atoms instance"""
        return "\n".join(atom.xyz_string for atom in self)

    @property
    def hash(self):
        """Returns a hash for the system which is just the atom names joined by a comma."""
        return ",".join(self.atom_names)

    def centre(
        self,
        centre_atom: Optional[Union[int, str, List[Union[Atom, str, int]]]] = None,
    ):
        """Centers the geometry on some atom. But this is still in GLOBAL Cartesian coordinates."""
        if isinstance(centre_atom, (int, str)):
            centre_atom = self[centre_atom]
        elif isinstance(centre_atom, list):
            centre_atom = self[centre_atom].centroid
        elif centre_atom is None:
            centre_atom = self.centroid

        for atom in self:
            atom.coordinates -= centre_atom

        self._centred = True

    def connectivity(
        self, connectivity_calculator: Callable[..., np.ndarray]
    ) -> np.ndarray:
        """Return the connectivity matrix (n_atoms x n_atoms) for the given Atoms instance.

        :param connectivity_calculator: connectivity calculator function that calculates connectivity
        :type connectivity_calculator: Callable[..., np.ndarray]
        :return: `np.ndarray` of shape n_atoms x n_atoms
        :rtype: np.ndarray
        """

        return connectivity_calculator(self)

    def alf(self, alf_calculator: Callable[..., ALF], *args, **kwargs) -> List[ALF]:
        """Returns the Atomic Local Frame (ALF) for all Atom instances that are held in Atoms
        e.g. [[0,1,2],[1,0,2], [2,0,1]]

        :param args: positional arguments to pass to alf calculator
        :param kwargs: key word arguments to pass to alf calculator
        """
        return [
            alf_calculator(atom_instance, *args, **kwargs) for atom_instance in self
        ]

    def alf_list(
        self, alf_calculator: Callable[..., ALF], *args, **kwargs
    ) -> List[List[int]]:
        """Returns a list of lists with the atomic local frame indices for every atom (0-indexed).

        :param args: positional arguments to pass to alf calculator
        :param kwargs: key word arguments to pass to alf calculator
        """
        return [
            ALF(alf.origin_idx, alf.x_axis_idx, alf.xy_plane_idx)
            for alf in self.alf(alf_calculator, *args, **kwargs)
        ]

    def alf_dict(
        self, alf_calculator: Callable[..., ALF], *args, **kwargs
    ) -> Dict[str, ALF]:
        """Returns a list of lists with the atomic local frame indices for every atom (0-indexed).

        :param args: positional arguments to pass to alf calculator
        :param kwargs: key word arguments to pass to alf calculator
        """
        return {
            atom_instance.name: atom_instance.alf(alf_calculator, *args, **kwargs)
            for atom_instance in self
        }

    def C_matrix_dict(self, system_alf: List[ALF]) -> Dict[str, np.ndarray]:
        """Returns a dictionary of key (atom name), value (C matrix np array) for every atom"""
        return {
            atom_instance.name: atom_instance.C(system_alf) for atom_instance in self
        }

    def C_matrix_list(self, system_alf: List[ALF]) -> List[np.ndarray]:
        """Returns a list C matrix np array for every atom"""
        return [atom_instance.C(system_alf) for atom_instance in self]

    # the feature calculator needs to be calculated for individual atoms
    # because we could only want the features for individual atoms
    # instead of for all atoms
    def features(
        self,
        feature_calculator: Callable[..., np.ndarray],
        *args,
        is_atomic=True,
        **kwargs,
    ) -> np.ndarray:
        """Returns the features for this Atoms instance,
        corresponding to the features of each Atom instance held in this Atoms isinstance
        Features are calculated in the Atom class and concatenated to a 2d array here.

        The array shape is n_atoms x n_features (3*n_atoms - 6)

        :param is_atomic: whether the feature calculator calculates features
            for individual atoms or for the whole geometry.
        :param args: positional arguments to pass to feature calculator
        :param kwargs: key word arguments to pass to feature calculator

        Returns:
            :type: `np.ndarray` of shape n_atoms x n_features (3N-6)
                Return the feature matrix of this Atoms instance
        """
        if is_atomic:
            return np.array(
                [
                    atom_instance.features(feature_calculator, *args, **kwargs)
                    for atom_instance in self
                ]
            )
        return feature_calculator(self, *args, **kwargs)

    def features_dict(
        self,
        feature_calculator: Callable[..., np.ndarray],
        *args,
        is_atomic=True,
        **kwargs,
    ) -> dict:
        """Returns the features in a dictionary for this Atoms instance,
        corresponding to the features of each Atom instance held in this Atoms isinstance
        Features are calculated in the Atom class and concatenated to a 2d array here.

        :param is_atomic: whether the feature calculator calculates features
            for per atom or for the whole geometry
        :param args: positional arguments to pass to feature calculator
        :param kwargs: key word arguments to pass to feature calculator

        e.g. {"C1": np.array, "H2": np.array}
        """

        if is_atomic:
            return {
                atom_instance.name: atom_instance.features(
                    feature_calculator, *args, **kwargs
                )
                for atom_instance in self
            }
        return {"atoms_features": feature_calculator(self, *args, **kwargs)}

    def kabsch(self, other: "Atoms") -> np.ndarray:
        H = self.coordinates.T.dot(other.coordinates)

        V, S, W = np.linalg.svd(H)
        d = (np.linalg.det(V) * np.linalg.det(W)) < 0.0

        if d:
            S[-1] = -S[-1]
            V[:, -1] = -V[:, -1]

        return np.dot(V, W)

    def rmsd(self, other: "Atoms"):
        if not self._centred:
            self.centre()
        if not other._centred:
            other.centre()

        R = self.kabsch(other)

        other.rotate(R)
        return self._rmsd(other)

    def rotate(self, R: np.ndarray):
        """Perform a rotation in 3D space with a matrix R. This rotates all atoms in the system the same amount.
        This method also changes the coordinates of the Atom instances held in the Atoms instance.
        """

        centroid = self.centroid
        self.centre()
        for atom in self:
            atom.coordinates = R.dot(atom.coordinates.T).T
        self.translate(centroid)

    def translate(self, v: np.ndarray):
        """Translates a system in 3D space.

        :param v: numpy array of shape (3,) which is added to the coordinates of each atom.
        """
        for atom in self:
            atom.coordinates += v

    def __getitem__(self, item) -> Union[Atom, "Atoms"]:
        """Used to index the Atoms isinstance with various types of `item`.

        e.g. we can index a variable atoms (which is an instance of Atoms) as atoms[0], or as atoms["C1"].
        In the first case, atoms[0] will return the 0th element (an Atom instance) held in this Atoms isinstance
        In the second case, atoms["C1] will return the Atom instance corresponding to atom with name C1."""

        if isinstance(item, str):
            for atom in self:
                if item.capitalize() == atom.name:
                    return atom
            raise KeyError(f"Atom '{item}' does not exist")
        elif isinstance(item, (list, np.ndarray, tuple)):
            if len(item) <= 0:
                return Atoms()
            if isinstance(item[0], (int, np.int, str)):
                return Atoms([self[i] for i in item])
            elif isinstance(item[0], bool):
                return Atoms(list(compress(self, item)))
        return super().__getitem__(item)

    def __delitem__(self, i: Union[int, str]):
        """deletes an instance of Atom from the self._atoms list (index i) if del is called on an Atoms instance
        e.g. del atoms[0], where atoms is an Atoms instance will delete the 0th element.
        del atoms["C1"] will delete the Atom instance with the name attribute of 'C1'."""

        if not isinstance(i, (int, str)):
            raise TypeError(
                f"Index {i} has to be of type int. Currently index is type {type(i)}"
            )
        else:
            del self[i]

    def __str__(self):
        return "\n".join(str(atom) for atom in self)

    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join(repr(atom) for atom in self)})"

    def __sub__(self, other):
        for i, atom in enumerate(self):
            for jatom in other:
                if jatom == atom:
                    del self[i]
        return self

    def __bool__(self):
        """Atoms instance evaluates as true if it contains
        Atom instances in it. If empty, the Atoms instance evaluates to False."""
        return bool(len(self))

    def _rmsd(self, other: "Atoms") -> float:
        dist = np.sum(
            np.sum(np.power(jatom.coordinates - iatom.coordinates, 2))
            for iatom, jatom in zip(self, other)
        )
        return np.sqrt(dist / len(self))
