# Skills in EduClaw Harness

EduClaw integrates with on-demand agent skills through `pydantic-ai-skills` and standard Agent Skills directories. When generating Manim scenes or handling complex mathematical visual workflows, the EduClaw Pydantic AI agent dynamically references domain rules, animation patterns, and LaTeX formulas.

---

## 1. Skill Locations in EduClaw

EduClaw discovers skills across multiple search directories:

1. **Package Built-in Skills (`.decode/skills/`)**: Bundled directly with EduClaw.
   - `manim-scene/`: Basic scene structure and construct methods.
   - `manim-quality/`: Manim quality flags and render profiles.
   - `manim-latex/`: LaTeX formulas, MathTex, and Tex expressions.
   - `manimce-best-practices/`: Comprehensive Manim Community Edition guide (from `adithya-s-k/manim_skill`).
   - `manimgl-best-practices/`: 3Blue1Brown OpenGL ManimGL guide (from `adithya-s-k/manim_skill`).
   - `manim-composer/`: 3b1b-style pedagogical structuring and `scenes.md` planning.

2. **Agent Skills Standards (`.agents/skills/`)**:
   - `educlaw-cli/`: CLI & TUI command workflows.
   - `manim-render/`: Docker sandbox rendering and FFmpeg container management.
   - `run-tests/`: Pytest and offline validation commands.

3. **Workspace/CWD Overrides**:
   - `<cwd>/.decode/skills/<skill_name>/`
   - `<cwd>/.agents/skills/<skill_name>/`

---

## 2. How to Install New Skills in EduClaw

### Method A: Automated via `npx skills`

Using `npx skills` or `skills.sh`, install skills directly into `.agents/skills` or `.decode/skills`:

```bash
# In the educlaw app directory (apps/educlaw):
npx skills add adithya-s-k/manim_skill/skills/manimce-best-practices
npx skills add adithya-s-k/manim_skill/skills/manimgl-best-practices
npx skills add adithya-s-k/manim_skill/skills/manim-composer
```

### Method B: Manual Installation

1. Create a skill subfolder under `.agents/skills/<skill-name>` or `.decode/skills/<skill-name>`:
   ```bash
   mkdir -p .agents/skills/my-custom-skill
   ```
2. Add a `SKILL.md` file with standard YAML frontmatter:
   ```markdown
   ---
   name: my-custom-skill
   description: Trigger when the user wants custom SVG morphing or shader effects in Manim.
   ---

   # My Custom Skill
   ## Rules & Code Examples
   ...
   ```
3. Optionally add `rules/`, `examples/`, `templates/`, and `references/` folders alongside `SKILL.md`.

---

## 3. How EduClaw Harness Uses Skills

- **Tool Registration**: `educlaw.agent.factory.build_agent` registers a `pydantic_ai_skills.SkillsToolset(directories=directories)` on the agent.
- **On-Demand Loading**: The system prompt instructs the agent:
  > *"load_skill only when you need a specific workflow — do not dump every skill"*
- **Execution & Validation**: The agent loads specific skill rules, writes the script with `sandbox_write`, and tests rendering with `manim_render` in the Docker sandbox.
