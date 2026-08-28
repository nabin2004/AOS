from __future__ import annotations

from typing import Optional, List, Dict, Tuple, Any
import numpy as np
from manim import (
    VGroup,
    ORIGIN,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig
from .atom import AtomMobject
from .bond import BondMobject


class Molecule2DMobject(VGroup):
    """2D Molecular representation connecting atoms with bonds."""

    def __init__(
        self,
        atoms_data: List[Tuple[str, list[float]]],  # [(symbol, [x, y, z])]
        bonds_data: List[Tuple[int, int, int]],    # [(atom_idx1, atom_idx2, bond_order)]
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()

        self.atoms: List[AtomMobject] = []
        self.bonds: List[BondMobject] = []

        # Create atoms
        for symbol, pos in atoms_data:
            atom = AtomMobject(symbol=symbol, theme=self.theme)
            atom.move_to(np.array(pos, dtype=float))
            self.atoms.append(atom)

        # Create bonds
        for idx1, idx2, order in bonds_data:
            p1 = self.atoms[idx1].circle.get_center()
            p2 = self.atoms[idx2].circle.get_center()
            bond = BondMobject(p1, p2, order=order, theme=self.theme)
            self.bonds.append(bond)
            self.add(bond)

        # Add atoms on top of bonds
        for atom in self.atoms:
            self.add(atom)

    @classmethod
    def create_water(cls, theme: Optional[ThemeConfig] = None) -> Molecule2DMobject:
        """Water molecule H2O (bent geometry ~104.5 degrees)."""
        angle = np.radians(52.25)
        dist = 1.2
        atoms = [
            ("O", [0.0, 0.3, 0.0]),
            ("H", [-dist * np.sin(angle), 0.3 - dist * np.cos(angle), 0.0]),
            ("H", [dist * np.sin(angle), 0.3 - dist * np.cos(angle), 0.0]),
        ]
        bonds = [(0, 1, 1), (0, 2, 1)]
        return cls(atoms, bonds, theme=theme)

    @classmethod
    def create_carbon_dioxide(cls, theme: Optional[ThemeConfig] = None) -> Molecule2DMobject:
        """Carbon dioxide CO2 (linear geometry 180 degrees)."""
        dist = 1.4
        atoms = [
            ("C", [0.0, 0.0, 0.0]),
            ("O", [-dist, 0.0, 0.0]),
            ("O", [dist, 0.0, 0.0]),
        ]
        bonds = [(0, 1, 2), (0, 2, 2)]
        return cls(atoms, bonds, theme=theme)

    @classmethod
    def create_benzene(cls, theme: Optional[ThemeConfig] = None) -> Molecule2DMobject:
        """Benzene ring C6H6."""
        radius = 1.5
        atoms = []
        for i in range(6):
            ang = np.radians(60 * i)
            atoms.append(("C", [radius * np.cos(ang), radius * np.sin(ang), 0.0]))
        bonds = [
            (0, 1, 2),
            (1, 2, 1),
            (2, 3, 2),
            (3, 4, 1),
            (4, 5, 2),
            (5, 0, 1),
        ]
        return cls(atoms, bonds, theme=theme)
