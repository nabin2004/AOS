"""Exporters for converting FlashcardDeck into Anki TSV, Markdown, and JSON formats."""

from __future__ import annotations

import re
from pathlib import Path

from educlaw.flashcards.contracts import CardType, ExportFormat, FlashcardDeck


def _sanitize_field(text: str) -> str:
    """Format multiline strings for Anki TSV: replace actual tabs and newlines with <br>."""
    if not text:
        return ""
    cleaned = text.strip().replace("\t", " ")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    # Replace single newlines with <br> so Anki renders multiline HTML cleanly on one TSV line
    cleaned = cleaned.replace("\n", "<br>")
    return cleaned


def export_to_anki_tsv(deck: FlashcardDeck, output_path: Path | None = None) -> str:
    """Export a FlashcardDeck to standard Anki-importable TSV / TXT format.

    Uses Anki metadata headers:
    #separator:tab
    #html:true
    #tags column:3
    """
    lines = [
        "#separator:tab",
        "#html:true",
        "#tags column:3",
    ]

    for card in deck.cards:
        # Determine Front content
        if card.card_type == CardType.CLOZE and card.cloze_text:
            front_text = card.cloze_text
        else:
            front_text = card.front

        # Build Back content
        back_parts = [card.back]
        if card.visual_cue:
            back_parts.append(f"<div style='color: #64B5F6; font-size: 0.9em; margin-top: 8px;'>🎬 <b>Visual Cue:</b> {card.visual_cue}</div>")

        back_text = "<br>".join(back_parts)

        # Tags
        tags_list = list(card.tags)
        if deck.course_slug:
            tags_list.append(f"course::{deck.course_slug}")
        if deck.lecture_number:
            tags_list.append(f"lecture::{deck.lecture_number:02d}")
        # Clean tags to ensure no spaces in individual tags
        formatted_tags = " ".join(re.sub(r"\s+", "_", t) for t in tags_list)

        sanitized_front = _sanitize_field(front_text)
        sanitized_back = _sanitize_field(back_text)

        lines.append(f"{sanitized_front}\t{sanitized_back}\t{formatted_tags}")

    content = "\n".join(lines)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    return content


def export_to_markdown(deck: FlashcardDeck, output_path: Path | None = None) -> str:
    """Export a FlashcardDeck to interactive, collapsible Markdown."""
    lines = [
        f"# 🎴 Flashcard Deck: {deck.title}",
        f"**Topic:** `{deck.topic}` | **Total Cards:** `{deck.total_cards}`",
        "",
        "> Click on any card below to reveal the answer and visual intuition.",
        "",
        "---",
        "",
    ]

    for idx, card in enumerate(deck.cards, start=1):
        type_badge = f"`[{card.card_type.value.upper()}]`"
        tags_str = " ".join(f"`#{t}`" for t in card.tags)

        lines.append(f"### Card {idx} {type_badge}")
        if card.card_type == CardType.CLOZE and card.cloze_text:
            lines.append(f"**Prompt (Cloze):** {card.cloze_text}")
        else:
            lines.append(f"**Question:** {card.front}")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary><b>🔍 Reveal Answer & Intuition</b></summary>")
        lines.append("")
        lines.append(card.back)
        if card.visual_cue:
            lines.append("")
            lines.append(f"🎬 **Visual Cue:** *{card.visual_cue}*")
        lines.append("</details>")
        if tags_str:
            lines.append("")
            lines.append(f"*Tags:* {tags_str}")
        lines.append("")
        lines.append("---")
        lines.append("")

    content = "\n".join(lines)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    return content


def export_deck(
    deck: FlashcardDeck,
    format_type: ExportFormat = ExportFormat.ANKI_TSV,
    output_path: Path | None = None,
) -> str:
    """Universal dispatcher for exporting flashcard decks."""
    if format_type == ExportFormat.ANKI_TSV:
        return export_to_anki_tsv(deck, output_path=output_path)
    elif format_type == ExportFormat.MARKDOWN:
        return export_to_markdown(deck, output_path=output_path)
    elif format_type == ExportFormat.JSON:
        content = deck.model_dump_json(indent=2)
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
        return content
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
