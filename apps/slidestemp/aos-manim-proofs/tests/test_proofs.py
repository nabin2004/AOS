import pytest
from aos_manim_core import get_theme, set_theme
from aos_manim_proofs import (
    ProofStep,
    ProofDocument,
    StepType,
    DerivationChain,
    ProofStructureValidator,
)


def test_proof_document_and_derivation_chain():
    set_theme("academic_oxford")
    step1 = ProofStep(
        id="s1",
        statement="a^2 - b^2 = a^2 - ab + ab - b^2",
        justification="Add and subtract ab",
        step_type=StepType.INFERENCE,
    )
    step2 = ProofStep(
        id="s2",
        statement="= a(a - b) + b(a - b)",
        justification="Factor by grouping",
        step_type=StepType.INFERENCE,
        depends_on=["s1"],
    )
    step3 = ProofStep(
        id="s3",
        statement="= (a - b)(a + b)",
        justification="Distributive property",
        step_type=StepType.QED,
        depends_on=["s2"],
    )

    doc = ProofDocument(
        theorem="a^2 - b^2 = (a - b)(a + b)",
        strategy="Direct",
        steps=[step1, step2, step3],
    )

    val = ProofStructureValidator()
    assert val.validate(doc).is_valid

    chain = DerivationChain(doc.theorem, doc.steps)
    assert len(chain) == 2  # header + step_mobs


def test_proof_structure_validator_error():
    step_invalid = ProofStep(
        id="s1",
        statement="x = y",
        justification="Premise",
        depends_on=["non_existent_step"],
    )
    doc_bad = ProofDocument(theorem="Test", strategy="Direct", steps=[step_invalid])
    val = ProofStructureValidator()
    assert not val.validate(doc_bad).is_valid
