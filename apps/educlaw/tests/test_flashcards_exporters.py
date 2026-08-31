from pathlib import Path
from educlaw.flashcards.contracts import CardType, ExportFormat, Flashcard, FlashcardDeck
from educlaw.flashcards.exporters import export_deck, export_to_anki_tsv, export_to_markdown


def test_export_to_anki_tsv(tmp_path):
    deck = FlashcardDeck(
        title="Fourier Analysis Flashcards",
        topic="Fourier Series",
        course_slug="fourier-analysis",
        lecture_number=1,
        cards=[
            Flashcard(
                card_type=CardType.BASIC,
                front="What are Fourier coefficients geometrically?",
                back="Projections of a signal onto orthogonal sinusoidal basis functions.",
                visual_cue="Rotating vectors projecting onto axes.",
                tags=["math::fourier"],
            ),
            Flashcard(
                card_type=CardType.CLOZE,
                front="The Fourier series decomposes {{c1::periodic functions}} into {{c2::sine and cosine harmonics}}.",
                back="Discovered by Joseph Fourier in 1822.",
                cloze_text="The Fourier series decomposes {{c1::periodic functions}} into {{c2::sine and cosine harmonics}}.",
                tags=["math::fourier", "cloze"],
            ),
        ],
    )

    tsv_file = tmp_path / "deck.anki.txt"
    content = export_to_anki_tsv(deck, output_path=tsv_file)

    assert tsv_file.exists()
    lines = content.splitlines()

    # Check Anki headers
    assert lines[0] == "#separator:tab"
    assert lines[1] == "#html:true"
    assert lines[2] == "#tags column:3"

    # Check line entries (tab separated)
    card1_cols = lines[3].split("\t")
    assert len(card1_cols) == 3
    assert "Fourier coefficients" in card1_cols[0]
    assert "Projections" in card1_cols[1]
    assert "Visual Cue:" in card1_cols[1]
    assert "course::fourier-analysis" in card1_cols[2]
    assert "lecture::01" in card1_cols[2]

    # Check Cloze line
    card2_cols = lines[4].split("\t")
    assert "{{c1::periodic functions}}" in card2_cols[0]


def test_export_to_markdown(tmp_path):
    deck = FlashcardDeck(
        title="Calculus Flashcards",
        topic="Derivatives",
        cards=[
            Flashcard(
                card_type=CardType.FORMULA,
                front="What is the product rule?",
                back="\\[ (uv)' = u'v + uv' \\]",
                tags=["math::calculus"],
            )
        ],
    )

    md_file = tmp_path / "deck.md"
    content = export_to_markdown(deck, output_path=md_file)

    assert md_file.exists()
    assert "# 🎴 Flashcard Deck: Calculus Flashcards" in content
    assert "<details>" in content
    assert "<summary>" in content
    assert "(uv)' = u'v + uv'" in content
