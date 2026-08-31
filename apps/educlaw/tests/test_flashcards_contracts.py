from uuid import uuid4
import pytest

from educlaw.flashcards.contracts import CardType, ExportFormat, Flashcard, FlashcardDeck


def test_flashcard_creation_and_cloze():
    card = Flashcard(
        card_type=CardType.CLOZE,
        front="The {{c1::Hamiltonian}} operator represents total energy.",
        back="In quantum mechanics, H is the observable corresponding to energy.",
        cloze_text="The {{c1::Hamiltonian}} operator represents total energy.",
        tags=["physics::quantum", "operator"],
    )

    assert card.card_type == CardType.CLOZE
    assert "{{c1::Hamiltonian}}" in card.cloze_text
    assert len(card.tags) == 2


def test_flashcard_deck_aggregation():
    deck = FlashcardDeck(
        title="Electromagnetism Basics",
        topic="Maxwell Equations",
        cards=[
            Flashcard(
                card_type=CardType.FORMULA,
                front="What is Gauss's Law in differential form?",
                back="\\[ \\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\varepsilon_0} \\]",
                tags=["physics::em"],
            ),
            Flashcard(
                card_type=CardType.BASIC,
                front="What is the physical meaning of Gauss's Law for Magnetism?",
                back="There are no isolated magnetic monopoles; magnetic field lines form closed loops.",
                tags=["physics::em"],
            ),
        ],
    )

    assert deck.total_cards == 2
    assert deck.topic == "Maxwell Equations"
