"""Courses and Lecture Series generation system for EduClaw."""

from educlaw.courses.contracts import (
    Audience,
    Course,
    CourseManifest,
    CourseSyllabus,
    GenerationMode,
    Lecture,
    LectureSpec,
    RenderStatus,
    VisualGrammar,
    slugify,
)
from educlaw.courses.orchestrator import CourseOrchestrator
from educlaw.courses.storage import (
    export_course_handbook,
    generate_syllabus_markdown,
    get_course_dir,
    get_courses_dir,
    list_courses,
    load_course,
    save_course,
)

__all__ = [
    "Audience",
    "Course",
    "CourseManifest",
    "CourseOrchestrator",
    "CourseSyllabus",
    "GenerationMode",
    "Lecture",
    "LectureSpec",
    "RenderStatus",
    "VisualGrammar",
    "export_course_handbook",
    "generate_syllabus_markdown",
    "get_course_dir",
    "get_courses_dir",
    "list_courses",
    "load_course",
    "save_course",
    "slugify",
]
