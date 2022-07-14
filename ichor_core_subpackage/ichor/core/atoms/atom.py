from typing import List, Optional, Union
from copy import deepcopy

import numpy as np
from ichor.core import constants
from ichor.core.common.types import Coordinates3D
from ichor.core.atoms.calculators.features import get_alf_feature_calculator

# from ichor.core.atoms.calculators import (ALFFeatureCalculator,
#                                           AtomSequenceALFCalculator)
from ichor.core.atoms.calculators import (
    ALF,
    ALFCalculatorFunction,
    FeatureCalculatorFunction,
    calculate_c_matrix,
    default_alf_calculator,
    default_feature_calculator,
)
from ichor.core.common.types import VarReprMixin
from ichor.core.units import AtomicDistance


class Atom(VarReprMixin, Coordinates3D):
    """
    The Atom class is used for ONE atom in ONE timestep.

    e.g. If we have 1000 timesteps in the trajectory, with 6 atoms in each timestep,
    the we will have 6000 Atom instances in total.
    """

    def __init__(
        self,
        ty: str,
        x: float,
        y: float,
        z: float,
        index: Optional[int] = None,
        parent: Optional["Atoms"] = None,
        units: AtomicDistance = AtomicDistance.Angstroms,
    ):
        # to be read in from coordinate line
        # element of atom
        self.type: str = ty.capitalize()
        # these are used for the actual names, eg. O1 H2 H3, so the atom_number starts at 1
        self._index: Optional[int] = index

        # we need the parent Atoms because we need to know what other atoms are in the system to calcualte ALF/features
        from ichor.core.atoms.atoms import Atoms

        self._parent: Optional[Atoms] = parent
        Coordinates3D.__init__(self, x, y, z)
        self.units: AtomicDistance = units

    @classmethod
    def from_atom(cls, atom: "Atom") -> "Atom":
        return Atom(
            atom.type,
            atom.x,
            atom.y,
            atom.z,
            atom._index,
            atom.parent,
            atom.units,
        )

    def to_angstroms(self) -> "Atom":
        """Convert the coordiantes to Angstroms"""
        new_atom = Atom.from_atom(self)
        if new_atom.units == AtomicDistance.Bohr:
            new_atom.coordinates *= constants.bohr2ang
        return new_atom

    def to_bohr(self) -> "Atom":
        """Convert the coordiantes to Bohr"""
        new_atom = Atom.from_atom(self)
        if new_atom.units == AtomicDistance.Angstroms:
            new_atom.coordinates *= constants.ang2bohr
        return new_atom

    @property
    def index(self) -> int:
        """Returns the integer assigned to the atom, calculated from the trajectory file. Indeces start at 1.
        This number is given to every atom in the trajectory, so atoms of the same type(element) can be distinguished."""
        if self._index is None:
            raise ValueError(
                f"'index' is not defined for '{self.__class__.__name__}({self.type} {self.x} {self.y} {self.z})'"
            )
        return self._index

    @index.setter
    def index(self, idx: int):
        self._index = idx

    @property
    def parent(self) -> "Atoms":
        if self._parent is None:
            raise ValueError(
                f"'parent' is not defined for '{self.__class__.__name__}({self.type} {self.x} {self.y} {self.z})'"
            )
        return self._parent

    @parent.setter
    def parent(self, parent: "Atoms"):
        self._parent = parent

    @property
    def nuclear_charge(self) -> float:
        return constants.type2nuclear_charge[self.type]

    @property
    def i(self) -> int:
        """Returns the index of the atom, if used in any arrays/list in Python."""
        return self.index - 1

    @property
    def name(self) -> str:
        """Returns the name of the Atom instance, which is later used to distinguish atoms when making GPR models.
        The number in the name starts at 1 (inclusive).
        e.g. O1"""
        return f"{self.type}{self.index}"

    @property
    def mass(self) -> float:
        """Returns the mass of the atom"""
        return round(constants.type2mass[self.type], 6)

    @property
    def radius(self):
        """Returns the Van der Waals radius of the given Atom instance."""
        return round(constants.type2rad[self.type], 2)

    @property
    def vdwr(self):  # todo: fix
        """Returns the Van der Waals radius of the given Atom instance."""
        return round(constants.type2vdwr[self.type], 2)

    @property
    def electronegativity(self):
        return constants.type2electronegativity[self.type]

    @property
    def valence(self):
        return constants.type2valence[self.type]

    @property
    def unpaired_electrons(self):
        return constants.type2orbital[self.type].value - self.valence

    @property
    def connectivity(self) -> np.ndarray:
        """
        Returns the 1D np.array corresponding to the connectivity of ONE Atom with respect to all other Atom
        instances that are held in an Atoms instance.
        This is only one row of the full connectivity matrix of the Atoms instance that is self._parent.
        """
        return self.parent.connectivity[self.i]

    @property
    def bonded_atoms(self) -> list:
        """Returns a list of Atom instances to which this Atom instance is connected

        Returns:
            :type: `list` of `Atom` instances
        """
        connectivity_matrix_row = self.connectivity
        return [
            self.parent[connected_atom]
            for connected_atom in connectivity_matrix_row.nonzero()[0]
        ]

    @property
    def bonded_atoms_names(self) -> list:
        """Returns a list of the names of Atom instances to which this Atom instance is connected

        Returns:
            :type: `list` of `str`
        """
        connectivity_matrix_row = self.connectivity
        return [
            self.parent[connected_atom].name
            for connected_atom in connectivity_matrix_row.nonzero()[0]
        ]

    def C(
        self, alf: Optional[Union[ALF, ALFCalculatorFunction]] = None
    ) -> np.ndarray:
        return calculate_c_matrix(self, alf=alf)

    def vec_to(self, other: "Atom") -> np.ndarray:
        """
        Calculates the vector from self to other
        :param other: atom to calculate the vector to
        :return: the vector from self to other as numpy array
        """
        return other.coordinates - self.coordinates

    def dist(self, other: "Atom") -> float:
        """
        Calculated the distance between self and other
        :param other: atom to calculate the distance to
        :return: the distance between self and other as a float
        """
        d = self.coordinates - other.coordinates
        return np.sqrt(d.dot(d))

    def angle(self, atom1: "Atom", atom2: "Atom") -> float:
        """
        Angle subtending atom1-self-atom2
        :param atom1: atom bonded to self
        :param atom2: other atom bonded to self
        :return: angle subtending atom1-self-atom2 as float
        """
        d1 = self.coordinates - atom1.coordinates
        d2 = self.coordinates - atom2.coordinates
        return np.arccos(
            d1.dot(d2) / (np.sqrt(d1.dot(d1)) * np.sqrt(d2.dot(d2)))
        )

    @property
    def bonded_atoms_i(self) -> list:
        """Returns a list of Atom indeces to which this Atom instance is connected

        Returns:
            :type: `list` of `int`, coresponding to the Atom instances indeces, as used in python lists (starting at 0).
        """
        connectivity_matrix_row = self.connectivity
        return [
            self.parent[connected_atom].i
            for connected_atom in connectivity_matrix_row.nonzero()[0]
        ]

    def alf(
        self,
        alf_calculator: ALFCalculatorFunction = default_alf_calculator,  # =AtomSequenceALFCalculator
    ) -> ALF:
        """Returns a list of the Atomic Local Frame (ALF). This ALF is ONLY for this Atom.

        e.g. If we have an Atoms instance for the water monomer, the ALF for the whole water monomer can be written as [[0,1,2], [1,0,2], [2,0,1]],
        while the ALF for the first atom only is [0,1,2]

        [0,1,2] contains the indeces for the central atom, x-axis atom, and xy-plane atom. These indeces start at 0 to index Python objects correctly.
        """
        return alf_calculator(self)

    @property
    def ialf(self) -> np.ndarray:
        """Returns a list containing the index of the central atom, the x-axis atom, and the xy-plane atom.
        THere indices are what are used in python lists (as they start at 0)."""
        alf = self.alf()
        return np.array([alf.origin_idx, alf.x_axis_idx, alf.xy_plane_idx])

    # @property
    # def C(self):
    #     """
    #     Mills, M.J.L., Popelier, P.L.A., 2014.
    #     Electrostatic Forces: Formulas for the First Derivatives of a Polarizable,
    #     Anisotropic Electrostatic Potential Energy Function Based on Machine Learning.
    #     Journal of Chemical Theory and Computation 10, 3840-3856.. doi:10.1021/ct500565g
    #
    #     Eq. 25-30
    #     """
    #     return calculate_c_matrix(self, self.alf())

    def features(
        self,
        feature_calculator: Union[ALF, FeatureCalculatorFunction] = default_feature_calculator,
    ) -> np.ndarray:
        """Returns a 1D 3N-6 np.ndarray of the features for the current Atom instance."""
        if isinstance(feature_calculator, ALF):
            feature_calculator = get_alf_feature_calculator(feature_calculator)

        return feature_calculator(self)

    @property
    def coordinates_string(self):
        width = str(16)
        precision = str(8)
        return f"{self.x:{width}.{precision}f}{self.y:{width}.{precision}f}{self.z:{width}.{precision}f}"

    @property
    def xyz_string(self):
        """Returns the atom type and coordinates for one Atom instance. This is used to write out an xyz file, which expects
        entries in the form of atom_type x_coordinate, y_coordinate, z_coordinate"""
        return f"{self.type:<3s}{self.coordinates_string}"

    def __str__(self):
        """Print out the atom name (containing atom type and index as used in model making), as well as
        coordinates of the atom
        """
        return f"{self.name} {self.coordinates_string}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name:<3s}{self.coordinates_string})"

    def __eq__(self, other: Union["Atom", int]):
        """Check if"""
        if isinstance(other, Atom):
            return (
                self.name == other.name
            )  # <- is this how we want to compare equality?
        # elif isinstance(other, int):  # <- this is a bit stupid and caused a lot of errors
        #     return self.index == other
        else:
            raise ValueError(
                f"Cannot compare type({type(other)}) with type({type(self)})"
            )

    def __hash__(self):
        return hash(str(self.index) + str(self.coordinates_string))

    def __sub__(self, other):
        self.coordinates -= other.coordinates
        return self
