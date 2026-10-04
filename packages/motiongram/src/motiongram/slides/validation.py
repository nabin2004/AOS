"""Validation engine for ManimGram Slides and narration bookmarks."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from motiongram.slides.schema import DeckSpec, SlideSpec

VALID_TEMPLATES = {
    "title_slide",
    "agenda_slide",
    "section_divider_slide",
    "bullet_reveal_slide",
    "concept_diagram_slide",
    "equation_slide",
    "derivation_slide",
    "comparison_slide",
    "summary_slide",
    "end_slide",
}


def extract_bookmarks(narration_text: str | None) -> list[str]:
    """Extract all bookmark identifiers defined in narration XML markup."""
    if not narration_text:
        return []
    # Matches <bookmark mark='...'/> or <bookmark mark="..." />
    pattern = r"<bookmark\s+mark=['\"]([A-Za-z0-9_]+)['\"]\s*/>"
    return re.findall(pattern, narration_text)


def validate_slide_bookmarks(slide: SlideSpec) -> tuple[list[str], list[str]]:
    """Validate bookmark triggers in timeline against narration text.

    Returns:
        (errors, warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []

    narration_text = slide.narration.text if slide.narration else ""
    defined_bookmarks = set(extract_bookmarks(narration_text))

    used_bookmarks: set[str] = set()
    for action in slide.timeline:
        if action.at.startswith("bookmark:"):
            bm_name = action.at.split("bookmark:", 1)[1].strip()
            used_bookmarks.add(bm_name)
            if bm_name not in defined_bookmarks:
                errors.append(
                    f"Slide '{slide.id}': Timeline action '{action.action}' references "
                    f"undefined bookmark '{bm_name}'. Available: {sorted(defined_bookmarks)}"
                )

    # Advisory warning for unused bookmarks
    unused = defined_bookmarks - used_bookmarks
    if unused:
        warnings.append(
            f"Slide '{slide.id}': Bookmarks defined but not used in timeline: {sorted(unused)}"
        )

    # Check narration length (~150 wpm)
    if narration_text:
        # Strip bookmark tags for word count
        clean_text = re.sub(r"<bookmark\s+mark=['\"][^'\"]*['\"]\s*/>", "", narration_text)
        word_count = len(clean_text.split())
        max_words = 130 if slide.template == "derivation_slide" else 95
        if word_count > max_words:
            warnings.append(
                f"Slide '{slide.id}': Narration contains {word_count} words "
                f"(max recommended: {max_words}). Consider splitting into two slides."
            )

    return errors, warnings


def validate_deck(deck: DeckSpec) -> tuple[bool, list[str], list[str]]:
    """Validate complete deck specification before compilation.

    Returns:
        (is_valid, errors, warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []

    slide_ids: set[str] = set()

    for idx, slide in enumerate(deck.slides):
        # 1. Slide ID uniqueness
        if not slide.id:
            errors.append(f"Slide at index {idx} has an empty 'id'.")
        elif slide.id in slide_ids:
            errors.append(f"Duplicate slide id '{slide.id}' detected at index {idx}.")
        else:
            slide_ids.add(slide.id)

        # 2. Template validity
        if slide.template not in VALID_TEMPLATES:
            errors.append(
                f"Slide '{slide.id}': Unknown template '{slide.template}'. "
                f"Valid templates: {sorted(VALID_TEMPLATES)}"
            )

        # 3. Bookmark validity
        slide_errors, slide_warnings = validate_slide_bookmarks(slide)
        errors.extend(slide_errors)
        warnings.extend(slide_warnings)

    is_valid = len(errors) == 0
    return is_valid, errors, warnings
