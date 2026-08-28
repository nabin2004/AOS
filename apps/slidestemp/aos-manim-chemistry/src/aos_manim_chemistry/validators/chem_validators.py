from __future__ import annotations

from typing import Any, List, Tuple
from aos_manim_core import BaseValidator, ValidationResult, ValidationSeverity
from ..structures.molecule import Molecule2DMobject


MAX_VALENCES = {
    "H": 1,
    "C": 4,
    "N": 4,
    "O": 2,
    "F": 1,
    "Cl": 1,
    "Br": 1,
    "I": 1,
    "S": 6,
    "P": 5,
}


class ValenceValidator(BaseValidator):
    """Verifies that atom bond totals in a Molecule2DMobject satisfy chemical valence rules."""

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(target, Molecule2DMobject):
            result.add_issue(
                code="INVALID_TARGET",
                message=f"Expected Molecule2DMobject, got {type(target).__name__}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        bond_counts = [0] * len(target.atoms)
        # Check bonds
        # Each bond connects two atoms with specific order
        # target.bonds contains BondMobjects
        for atom_idx, atom in enumerate(target.atoms):
            sym = atom.symbol
            max_v = MAX_VALENCES.get(sym, 8)
            # count bonds connected to this atom
            total_bonds = 0
            for b in target.bonds:
                # check if atom center matches bond endpoints
                p = atom.circle.get_center()
                # If within tolerance of start or end
                for line in b:
                    p1 = line.get_start()
                    p2 = line.get_end()
                    import numpy as np
                    if np.linalg.norm(p - p1) < 0.2 or np.linalg.norm(p - p2) < 0.2:
                        total_bonds += 1
                        break
            if total_bonds > max_v:
                result.add_issue(
                    code="VALENCE_CAPACITY_EXCEEDED",
                    message=f"Atom {sym} at index {atom_idx} has {total_bonds} bonds > max {max_v}",
                    severity=ValidationSeverity.ERROR,
                    details={"symbol": sym, "bonds": total_bonds, "max_valence": max_v},
                )

        return result
