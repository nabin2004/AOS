# Agent Skills Guide: Installation & Usage in AOS Harness

This guide explains how Agent Skills work in the **AOS (Agentic Orchestration System)** harness and AI coding agents (Antigravity, OpenCode, Claude Code, Cursor, Codex), and how to install or create new skills.

---

## 1. What are Agent Skills?

An **Agent Skill** is a modular, on-demand bundle of domain knowledge, best practices, reference patterns, code examples, and prompt instructions that AI coding assistants load when performing specialized tasks.

Skills follow the open [Agent Skills specification](https://github.com/anthropics/skills):
- Each skill resides in its own directory: `.agents/skills/<skill-name>/`
- The core entry point is **`SKILL.md`** with standard YAML frontmatter:
  ```yaml
  ---
  name: <skill-name>
  description: Trigger condition and summary of what the skill provides.
  ---
  ```
- Optional supplementary subdirectories:
  - `rules/`: Detailed modular rules and domain constraints.
  - `examples/`: Tested, production-ready code samples.
  - `templates/`: Boilerplate starter scenes and templates.
  - `references/`: Architecture notes, APIs, or cheat sheets.
  - `scripts/`: Executable utility scripts or benchmarks.

---

## 2. Installed Manim Skills in AOS

The following skills from [`adithya-s-k/manim_skill`](https://github.com/adithya-s-k/manim_skill) and AOS internal pipelines are configured in `.agents/skills/`:

| Skill Name | Path | Purpose |
|------------|------|---------|
| **`manimce-best-practices`** | [`.agents/skills/manimce-best-practices/SKILL.md`](.agents/skills/manimce-best-practices/SKILL.md) | Best practices, patterns, and examples for **Manim Community Edition** (`from manim import *`). |
| **`manimgl-best-practices`** | [`.agents/skills/manimgl-best-practices/SKILL.md`](.agents/skills/manimgl-best-practices/SKILL.md) | Best practices for **ManimGL / 3b1b edition** (`from manimlib import *`, OpenGL, interactive scene). |
| **`manim-composer`** | [`.agents/skills/manim-composer/SKILL.md`](.agents/skills/manim-composer/SKILL.md) | Planning & composing 3Blue1Brown-style pedagogical scripts, narrative hooks, and `scenes.md`. |
| **`manim-render`** | [`.agents/skills/manim-render/SKILL.md`](.agents/skills/manim-render/SKILL.md) | Docker rendering execution, ffmpeg assembly, and container management. |
| **`run-lecture-pipeline`** | [`.agents/skills/run-lecture-pipeline/SKILL.md`](.agents/skills/run-lecture-pipeline/SKILL.md) | Execution guide for the end-to-end multi-agent lecture generation pipeline. |
| **`sft-trace-collection`** | [`.agents/skills/sft-trace-collection/SKILL.md`](.agents/skills/sft-trace-collection/SKILL.md) | Synthetic prompt generation, trajectory collection, and SFT/DPO dataset builds. |

---

## 3. How to Install Skills in the Harness

### Method A: Automated Installation with `npx skills` (Recommended)

Using [`skills.sh`](https://skills.sh/) or `npx skills`, you can install skills directly from any GitHub repository:

```bash
# Install Manim Community Edition skills
npx skills add adithya-s-k/manim_skill/skills/manimce-best-practices

# Install ManimGL skills
npx skills add adithya-s-k/manim_skill/skills/manimgl-best-practices

# Install Manim Composer skill
npx skills add adithya-s-k/manim_skill/skills/manim-composer

# Or install from any public GitHub repository:
npx skills add <github-user>/<repo>/skills/<skill-name>
```

### Method B: Manual Git Submodule / Copy (Workspace-Level)

To add skills directly to this repository:

1. Clone or download the target skill directory.
2. Place the folder under `.agents/skills/<skill-name>/`.
3. Verify that `.agents/skills/<skill-name>/SKILL.md` exists and includes valid YAML frontmatter:
   ```markdown
   ---
   name: my-new-skill
   description: Brief description of when to activate this skill.
   ---

   # My New Skill
   Detailed instructions, usage rules, and guidelines...
   ```

### Method C: Global Installation (Across All Projects)

If you want skills to be available in every workspace on your machine for Antigravity or OpenCode:

- **Windows**: Copy skill folders to `%USERPROFILE%\.gemini\config\skills\<skill-name>\`
- **Linux/macOS**: Copy skill folders to `~/.gemini/config/skills/<skill-name>/` or `~/.agents/skills/<skill-name>/`

---

## 4. How the Agent Harness Discovers & Activates Skills

When an AI agent (such as Antigravity, OpenCode, or Pydantic AI Graph) starts a task:

1. **Discovery**: The harness scans the customization root (`.agents/skills/` in the workspace and `~/.gemini/config/skills/` globally).
2. **Context Indexing**: The agent context receives the skill names and descriptions.
3. **Selective Activation**: When the agent recognizes a relevant prompt (e.g. `from manim import *`, "create a 3b1b animation", or "render scene"), it reads the relevant `SKILL.md` and related rules.
4. **Execution**: The agent adheres to the patterns, avoiding common bugs (such as LaTeX compilation failures, mismatched imports, or Docker container leaks).

---

## 5. Creating a Custom Skill for AOS

To add your own custom skill for AOS agents:

1. Create a new directory in `.agents/skills/`:
   ```bash
   mkdir -p .agents/skills/my-custom-skill
   ```
2. Create `.agents/skills/my-custom-skill/SKILL.md`:
   ```markdown
   ---
   name: my-custom-skill
   description: Use this skill when generating custom Manim audio graphs or evaluating TTS latency.
   ---

   # Custom Skill Title

   ## When to Use
   Describe activation triggers.

   ## Guidelines & Patterns
   - Rule 1: Always test with `uv run python ...`
   - Rule 2: Follow IR schema definitions in `packages/ir/`
   ```
3. Add any supporting examples under `.agents/skills/my-custom-skill/examples/`.
