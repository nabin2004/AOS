"""Storage, manifest management, and persistence for Courses and Lectures."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from educlaw.courses.contracts import Course, CourseManifest, CourseSyllabus, Lecture, RenderStatus


def get_courses_dir(workspace_dir: Path | None = None) -> Path:
    """Get the root courses storage directory."""
    cwd = workspace_dir or Path.cwd()
    courses_dir = cwd / ".educlaw" / "courses"
    courses_dir.mkdir(parents=True, exist_ok=True)
    return courses_dir


def get_course_dir(course_slug: str, workspace_dir: Path | None = None) -> Path:
    """Get the directory path for a specific course slug."""
    courses_dir = get_courses_dir(workspace_dir)
    return courses_dir / course_slug


def generate_syllabus_markdown(syllabus: CourseSyllabus) -> str:
    """Generate a clean, beautiful Markdown representation of the course syllabus."""
    lines = [
        f"# 📚 {syllabus.title}",
        f"**Subject:** {syllabus.subject} | **Target Audience:** {syllabus.target_audience.value.title() if hasattr(syllabus.target_audience, 'value') else syllabus.target_audience}",
        "",
        "## 🎯 Course Overview",
        syllabus.overview,
        "",
    ]
    if syllabus.learning_outcomes:
        lines.append("## 🏆 Learning Outcomes")
        for outcome in syllabus.learning_outcomes:
            lines.append(f"- {outcome}")
        lines.append("")

    lines.append("## 🎨 Visual Grammar & Theme")
    lines.append(f"- **Palette:** {syllabus.visual_grammar.theme_name} (Primary: `{syllabus.visual_grammar.primary_color}`, Secondary: `{syllabus.visual_grammar.secondary_color}`, Accent: `{syllabus.visual_grammar.accent_color}`)")
    lines.append(f"- **Background:** `{syllabus.visual_grammar.background_color}`")
    lines.append("")

    lines.append("## 📖 Lectures Schedule")
    for spec in syllabus.lectures:
        lines.append(f"### Lecture {spec.lecture_number}: {spec.title}")
        lines.append(f"*{spec.description}*")
        lines.append("")
        if spec.key_concepts:
            lines.append(f"- **Key Concepts:** {', '.join(spec.key_concepts)}")
        if spec.prerequisites_from_course:
            lines.append(f"- **Prerequisites from course:** {', '.join(spec.prerequisites_from_course)}")
        if spec.visual_goals:
            lines.append(f"- **Visual Goals:** {', '.join(spec.visual_goals)}")
        lines.append(f"- **Estimated Duration:** ~{spec.estimated_duration_minutes} min")
        lines.append("")

    return "\n".join(lines)


def build_manifest(course: Course) -> CourseManifest:
    """Build a CourseManifest snapshot from a Course object."""
    rendered_count = sum(1 for lec in course.lectures if lec.is_rendered)
    lectures_summary = [
        {
            "lecture_number": lec.lecture_number,
            "title": lec.spec.title,
            "status": lec.status.value,
            "video_path": lec.video_path,
            "has_code": lec.final_code is not None,
            "has_notes": lec.study_notes is not None,
        }
        for lec in course.lectures
    ]
    return CourseManifest(
        course_id=str(course.course_id),
        title=course.title,
        slug=course.slug,
        subject=course.syllabus.subject,
        target_audience=course.syllabus.target_audience.value if hasattr(course.syllabus.target_audience, "value") else str(course.syllabus.target_audience),
        total_lectures=len(course.lectures),
        rendered_lectures=rendered_count,
        created_at=course.created_at,
        updated_at=course.updated_at,
        lectures_summary=lectures_summary,
    )


def save_course(course: Course, workspace_dir: Path | None = None) -> Path:
    """Persist a complete Course object, its syllabus, manifest, and lecture artifacts to disk."""
    course.updated_at = datetime.now(timezone.utc).isoformat()
    course_dir = get_course_dir(course.slug, workspace_dir)
    course_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save course.json (complete state)
    course_json_path = course_dir / "course.json"
    course_json_path.write_text(course.model_dump_json(indent=2), encoding="utf-8")

    # 2. Save course_manifest.json (lightweight index)
    manifest = build_manifest(course)
    manifest_path = course_dir / "course_manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    # 3. Save syllabus.md
    syllabus_md_path = course_dir / "syllabus.md"
    syllabus_md_path.write_text(generate_syllabus_markdown(course.syllabus), encoding="utf-8")

    # 4. Save per-lecture folders and files
    for lecture in course.lectures:
        lec_dir = course_dir / f"lecture_{lecture.lecture_number:02d}"
        lec_dir.mkdir(parents=True, exist_ok=True)

        # Code
        if lecture.final_code:
            code_file = lec_dir / "scene.py"
            code_file.write_text(lecture.final_code.code, encoding="utf-8")

        # Narration Plan
        if lecture.narration_plan:
            narr_file = lec_dir / "narration.json"
            narr_file.write_text(lecture.narration_plan.model_dump_json(indent=2), encoding="utf-8")

        # Study Notes
        if lecture.study_notes:
            notes_file = lec_dir / "notes.md"
            notes_file.write_text(lecture.study_notes, encoding="utf-8")

    return course_dir


def load_course(slug_or_id: str, workspace_dir: Path | None = None) -> Course | None:
    """Load a Course object from disk by slug or course ID."""
    courses_dir = get_courses_dir(workspace_dir)

    # Check direct slug directory
    direct_dir = courses_dir / slug_or_id
    if direct_dir.is_dir() and (direct_dir / "course.json").is_file():
        try:
            data = json.loads((direct_dir / "course.json").read_text(encoding="utf-8"))
            return Course.model_validate(data)
        except Exception:
            pass

    # Search all directories for matching slug or course_id
    for item in courses_dir.iterdir():
        if item.is_dir() and (item / "course.json").is_file():
            try:
                data = json.loads((item / "course.json").read_text(encoding="utf-8"))
                course = Course.model_validate(data)
                if course.slug == slug_or_id or str(course.course_id) == slug_or_id:
                    return course
            except Exception:
                continue

    return None


def list_courses(workspace_dir: Path | None = None) -> list[CourseManifest]:
    """List all courses found in the workspace storage."""
    courses_dir = get_courses_dir(workspace_dir)
    manifests: list[CourseManifest] = []

    for item in courses_dir.iterdir():
        if not item.is_dir():
            continue
        manifest_file = item / "course_manifest.json"
        course_file = item / "course.json"

        if manifest_file.is_file():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifests.append(CourseManifest.model_validate(data))
                continue
            except Exception:
                pass

        if course_file.is_file():
            try:
                data = json.loads(course_file.read_text(encoding="utf-8"))
                course = Course.model_validate(data)
                manifests.append(build_manifest(course))
            except Exception:
                pass

    manifests.sort(key=lambda m: m.created_at, reverse=True)
    return manifests


def export_course_handbook(course: Course, output_file: Path | None = None) -> str:
    """Compile the syllabus and all lecture notes into a single cohesive Markdown study handbook."""
    sections = [
        f"# {course.title} — Complete Course Handbook",
        f"*Generated by EduClaw Course Engine on {course.created_at[:10]}*",
        "\n---\n",
        generate_syllabus_markdown(course.syllabus),
        "\n---\n",
    ]

    for lec in course.lectures:
        sections.append(f"# Part {lec.lecture_number}: {lec.spec.title}\n")
        if lec.study_notes:
            sections.append(lec.study_notes)
        else:
            sections.append(f"*{lec.spec.description}*")
        sections.append("\n---\n")

    full_text = "\n\n".join(sections)
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(full_text, encoding="utf-8")
    return full_text
