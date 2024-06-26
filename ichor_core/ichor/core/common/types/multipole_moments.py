from collections import namedtuple

MolecularDipole = namedtuple("MolecularDipole", "x y z")
MolecularQuadrupole = namedtuple("MolecularQuadrupole", "xx yy zz xy xz yz")
TracelessMolecularQuadrupole = namedtuple(
    "TracelessMolecularQuadrupole", "xx yy zz xy xz yz"
)
MolecularOctupole = namedtuple(
    "MolecularOctupole", "xxx yyy zzz xyy xxy xxz xzz yzz yyz xyz"
)
MolecularHexadecapole = namedtuple(
    "MolecularHexadecapole",
    "xxxx yyyy zzzz xxxy xxxz yyyx yyyz zzzx zzzy xxyy xxzz yyzz xxyz yyxz zzxy",
)
