# Flashcard Agent & Anki Deck Generator

> **Automated Active Recall Extraction, Cloze Deletions, Visual Geometry Cues, and Anki-Compatible Deck Exporter**

---

## 🎯 Overview

The **Flashcard Generation Engine** (`educlaw.flashcards`) allows users to automatically generate high-yield, conceptually rigorous flashcards from educational videos, Manim animation code, voiceover narration scripts, and companion lecture notes.

The system produces standard **Anki-importable TSV / TXT files** (`.anki.txt`), interactive collapsible Markdown study decks (`.md`), and JSON models.

---

## 🃏 Supported Card Types

1. **Basic Conceptual Cards (`basic`)**:
   - Tests core mechanisms, causal chains, and foundational definitions.
   - Front: Precise question forcing active memory retrieval.
   - Back: Conceptual explanation with visual intuition cues.
2. **Cloze Deletion Cards (`cloze`)**:
   - Formatted with standard Anki cloze syntax: `{{c1::key concept}}`.
   - Ideal for active recall of terminology, constants, and theorem names.
3. **Formula & Equation Cards (`formula`)**:
   - Encodes mathematical formulas using LaTeX delimiters: `\( ... \)` and `\[ ... \]`.
   - Explains the physical or geometric meaning of each variable.
4. **Visual Intuition Cards (`visual_intuition`)**:
   - Directly tests the geometric behavior, path divergence, or coordinate transformations visualized in the Manim video.

---

## 📥 Anki TSV Format Compliance

Exported decks use the official Anki text import specification:
```tsv
#separator:tab
#html:true
#tags column:3
What is the geometric meaning of the determinant of a 2x2 matrix?	The factor by which the linear transformation scales <b>area</b> in 2D space.<br><div style='color: #64B5F6; font-size: 0.9em; margin-top: 8px;'>🎬 <b>Visual Cue:</b> Unit square transforming into a parallelogram.</div>	math::linear-algebra educlaw
The eigenvalue equation is expressed as {{c1::A \vec{v} = \lambda \vec{v}}}.	Where \(\vec{v}\) is the eigenvector and \(\lambda\) is the scaling factor.	math::linear-algebra cloze
```

To import into Anki:
1. Open **Anki Desktop**.
2. Click **File $\to$ Import...**
3. Select the generated `.anki.txt` file.
4. Anki automatically maps fields to `Front`, `Back`, and `Tags`.

---

## 💻 CLI Commands

### 1. Generate Flashcards for Any Topic
```powershell
# Export as Anki-compatible TSV/TXT (default)
educlaw flashcards new "Eigenvectors and Eigenvalues" --format anki --output eigen_deck.anki.txt

# Export as Interactive Markdown (with collapsible <details> tags)
educlaw flashcards new "Calculus Derivatives" --format md --output derivatives.md
```

### 2. Generate Flashcards for a Course Lecture
```powershell
# Generate flashcards specifically for Lecture 2 of a course
educlaw course flashcards linear-algebra-fundamentals --lecture 2 --format anki

# Generate flashcards for all lectures in the course
educlaw course flashcards linear-algebra-fundamentals --format anki
```

---

## 🧪 Testing

Run the flashcard test suite:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_flashcards_contracts.py tests/test_flashcards_exporters.py tests/test_flashcards_cli.py -v
```
