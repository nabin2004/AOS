"""
AOS Manim Proofs: Mathematical proof trees and step-by-step derivations.
"""

from .structures.proof_step import ProofStep, ProofDocument, StepType
from .structures.derivation_chain import DerivationChain
from .validators.proof_validators import ProofStructureValidator

__version__ = "0.1.0"

__all__ = [
    "ProofStep",
    "ProofDocument",
    "StepType",
    "DerivationChain",
    "ProofStructureValidator",
]
