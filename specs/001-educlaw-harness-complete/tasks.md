# Implementation Tasks: 001-educlaw-harness-complete

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency setup

- [X] T001 Add `ffmpeg-python` and `pillow` dependencies to `apps/educlaw/pyproject.toml`
- [X] T002 [P] Create `.aos/trajectories/` directory for trajectory logging

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**🛑 CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Ensure existing Dagestan memory schema and DockerSandbox are fully updated for new tools

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Pedagogical Visual Design & Theme System (Priority: P1) 🚀 MVP

**Goal**: Provide a declarative Manim theme engine (`EduClawTheme`), pre-designed palettes, visual component templates, and pacing rules.

**Independent Test**: Theme colors and component snippets load correctly and are injected into the agent context.

### Tests for User Story 1 (OPTIONAL - only if tests requested) 🧪
- [X] T004 [P] [US1] Create unit tests for theme engine and component library in `apps/educlaw/tests/test_theme_and_components.py`

### Implementation for User Story 1
- [X] T005 [P] [US1] Create `EduClawTheme` and `ColorPalette` models in `apps/educlaw/educlaw/animateworkflow/theme.py`
- [X] T006 [P] [US1] Create `ComponentSnippet` model and templates (MathCallout, ProofContainer, CodeWindow) in `apps/educlaw/educlaw/animateworkflow/components.py`
- [X] T007 [US1] Update `CodeGeneratorAgent` context prompt to inject `EduClawTheme` and `ComponentSnippet`s
- [X] T008 [US1] Implement micro-pacing syllable count calculations in code generation instructions
- [X] T009 [US1] Add `--theme` flag to Typer CLI in `apps/educlaw/educlaw/cli.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Native Manim Voiceover & Timestamp Aligner (Priority: P1)

**Goal**: Sync Manim bookmark timing tags with voiceover narration within the Docker sandbox.

**Independent Test**: Generated Manim code uses `with self.voiceover(...)` and `wait_until_bookmark()` successfully.

### Implementation for User Story 2
- [X] T010 [P] [US2] Implement `ManimVoiceoverService` adapter for PocketTTS/KyutaiDSM in `apps/educlaw/sandbox/docker.py`
- [X] T011 [US2] Update `validator.py` to enforce `<bookmark>` tag presence and voiceover context manager usage
- [X] T012 [US2] Update `CodeGeneratorAgent` prompt to instruct precise bookmark-to-animation synchronization

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Advanced Harness Tooling & API Inspection (Priority: P2)

**Goal**: Add Manim API lookup tool, multi-scene video concatenation tool, and trajectory logging hook.

**Independent Test**: Agents can lookup ManimCE signatures without hallucinations and stitch videos.

### Tests for User Story 3
- [X] T013 [P] [US3] Create API lookup tool unit test in `apps/educlaw/tests/test_manim_kb.py`

### Implementation for User Story 3
- [X] T014 [P] [US3] Create `ManimSymbolDoc` model and index ManimCE classes/animations in `apps/educlaw/educlaw/animateworkflow/manim_kb.py`
- [X] T015 [US3] Implement `manim_api_lookup` tool in `apps/educlaw/educlaw/agent/tools.py`
- [X] T016 [US3] Implement `manim_concat_scenes` tool using ffmpeg in `apps/educlaw/educlaw/agent/tools.py`
- [X] T017 [US3] Implement trajectory logging hook (JSONL) mapped to `.aos/trajectories/`
- [X] T018 [US3] Register tools and add `--concat` flag to `apps/educlaw/educlaw/cli.py`

**Checkpoint**: All tools available to agents for building complex scenes

---

## Phase 6: User Story 4 - Multimodal Visual Quality Control (Priority: P3)

**Goal**: Implement keyframe extraction and multimodal visual inspection tool to prevent text overlap or truncation.

**Independent Test**: Keyframes extract correctly and QC agent accurately identifies overlapping text.

### Tests for User Story 4
- [X] T019 [P] [US4] Create visual QC evaluation test in `apps/educlaw/tests/test_visual_qc.py`

### Implementation for User Story 4
- [X] T020 [P] [US4] Create `VisualQCReport` and `FrameInspection` models in `apps/educlaw/educlaw/animateworkflow/contracts.py`
- [X] T021 [US4] Implement `ffmpeg` keyframe extraction and `visual_qc_check` tool in `apps/educlaw/educlaw/animateworkflow/visual_qc.py`
- [X] T022 [US4] Register `visual_qc_check` tool in `apps/educlaw/educlaw/agent/tools.py`
- [X] T023 [US4] Integrate Visual QC gate into `step_generate_and_compile` failure classification loop in `apps/educlaw/educlaw/animateworkflow/loop.py`
- [X] T024 [US4] Add `--inspect-visual` flag to `apps/educlaw/educlaw/cli.py`

**Checkpoint**: Full auto-correction and visual quality assurance enabled

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T025 [P] Update documentation in `apps/educlaw/docs/` for new tools and themes
- [X] T026 Execute end-to-end `quickstart.md` validation scenarios
- [X] T027 Code cleanup, linting, and type hint verification across `apps/educlaw/educlaw/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion
- **User Stories (Phase 3+)**: Depend on Foundational phase completion
  - US1 (Theme), US2 (Audio Sync), and US3 (Tooling) can proceed in parallel
  - US4 (Visual QC) should follow US3 since it relies on advanced compilation mechanics
- **Polish (Final Phase)**: Depends on all user stories being complete

### Parallel Opportunities

- Task T002 can run in parallel with dependency installation (T001).
- All unit test creations (T004, T013, T019) can be drafted in parallel.
- Data models (`EduClawTheme`, `ColorPalette`, `ComponentSnippet`, `ManimSymbolDoc`, `VisualQCReport`) can be scaffolded concurrently.
- US1, US2, and US3 can be executed independently.

---

## Parallel Example: User Story 1

```bash
# Launch test and models in parallel:
Task: "T004 [P] [US1] Create unit tests for theme engine and component library"
Task: "T005 [P] [US1] Create EduClawTheme and ColorPalette models"
Task: "T006 [P] [US1] Create ComponentSnippet model and templates"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup + Foundational
2. Implement User Story 1 (Theme & Visual Components)
3. **STOP and VALIDATE**: Test theme injection independently

### Incremental Delivery

1. Implement US1 (Themes) -> Validated
2. Implement US2 (Voiceover Bookmark Sync) -> Validated
3. Implement US3 (Tools & Concat) -> Validated
4. Implement US4 (Visual QC Gate) -> Final Pipeline Validation
