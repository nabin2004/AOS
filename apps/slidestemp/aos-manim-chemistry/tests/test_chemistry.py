import pytest
from aos_manim_core import get_theme, set_theme
from aos_manim_chemistry import (
    AtomMobject,
    BondMobject,
    Molecule2DMobject,
    ValenceValidator,
)


def test_atom_and_bond_mobjects():
    set_theme("academic_oxford")
    atom_o = AtomMobject("O")
    assert atom_o.symbol == "O"
    assert len(atom_o) == 2

    bond = BondMobject([0, 0, 0], [1, 0, 0], order=2)
    assert len(bond) == 2


def test_molecule_templates():
    h2o = Molecule2DMobject.create_water()
    assert len(h2o.atoms) == 3
    assert len(h2o.bonds) == 2

    co2 = Molecule2DMobject.create_carbon_dioxide()
    assert len(co2.atoms) == 3
    assert len(co2.bonds) == 2

    benzene = Molecule2DMobject.create_benzene()
    assert len(benzene.atoms) == 6
    assert len(benzene.bonds) == 6


def test_valence_validator():
    h2o = Molecule2DMobject.create_water()
    val = ValenceValidator()
    assert val.validate(h2o).is_valid
