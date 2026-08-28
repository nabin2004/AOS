from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class StepType(str, Enum):
    ASSUMPTION = "ASSUMPTION"
    AXIOM = "AXIOM"
    LEMMA = "LEMMA"
    INFERENCE = "INFERENCE"
    CONTRADICTION = "CONTRADICTION"
    QED = "QED"


@dataclass
class ProofStep:
    id: str
    statement: str
    justification: str
    step_type: StepType = StepType.INFERENCE
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ProofDocument:
    theorem: str
    strategy: str  # Direct, Contradiction, Induction, Contrapositive
    assumptions: List[str] = field(default_factory=list)
    steps: List[ProofStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theorem": self.theorem,
            "strategy": self.strategy,
            "assumptions": self.assumptions,
            "steps": [
                {
                    "id": s.id,
                    "statement": s.statement,
                    "justification": s.justification,
                    "step_type": s.step_type.value,
                    "depends_on": s.depends_on,
                }
                for s in self.steps
            ],
        }
