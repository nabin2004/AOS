from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional, Union

from .models import CourseRecord, LectureRecord
from .paths import courses_dir, lectures_dir


def save_lecture(record: LectureRecord) -> Path:
    path = lectures_dir() / f"{record.id}.json"
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return path


def save_course(record: CourseRecord) -> Path:
    path = courses_dir() / f"{record.id}.json"
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_lecture(lecture_id: str) -> Optional[LectureRecord]:
    path = lectures_dir() / f"{lecture_id}.json"
    if not path.exists():
        return None
    return LectureRecord.model_validate_json(path.read_text(encoding="utf-8"))


def load_course(course_id: str) -> Optional[CourseRecord]:
    path = courses_dir() / f"{course_id}.json"
    if not path.exists():
        return None
    return CourseRecord.model_validate_json(path.read_text(encoding="utf-8"))


def list_lectures() -> list[LectureRecord]:
    records = [
        LectureRecord.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(lectures_dir().glob("*.json"))
    ]
    records.sort(key=lambda r: r.created_at, reverse=True)
    return records


def list_courses() -> list[CourseRecord]:
    records = [
        CourseRecord.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(courses_dir().glob("*.json"))
    ]
    records.sort(key=lambda r: r.created_at, reverse=True)
    return records


def _matches(query: str, *fields: str) -> bool:
    q = query.strip().lower()
    return any(q in f.lower() for f in fields if f)


def search_lectures(query: str) -> list[LectureRecord]:
    return [
        r for r in list_lectures()
        if _matches(query, r.topic, r.subject, r.query, r.id)
    ]


def search_courses(query: str) -> list[CourseRecord]:
    return [
        r for r in list_courses()
        if _matches(query, r.topic, r.subject, r.query, r.id)
    ]


def resolve(id_or_prefix: str) -> Optional[tuple[Literal["lecture", "course"], Union[LectureRecord, CourseRecord]]]:
    """Find a lecture or course by exact id or unambiguous id prefix."""
    exact_lecture = load_lecture(id_or_prefix)
    if exact_lecture is not None:
        return "lecture", exact_lecture
    exact_course = load_course(id_or_prefix)
    if exact_course is not None:
        return "course", exact_course

    prefix_lectures = [r for r in list_lectures() if r.id.startswith(id_or_prefix)]
    prefix_courses = [r for r in list_courses() if r.id.startswith(id_or_prefix)]
    matches = [("lecture", r) for r in prefix_lectures] + [("course", r) for r in prefix_courses]
    if len(matches) == 1:
        return matches[0]
    return None
