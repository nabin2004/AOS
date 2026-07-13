from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .generator import build_lecture_ir, new_id, normalize_subject
from .models import CourseRecord, LectureRecord
from .paths import data_dir, players_dir
from .player import render_course_player, render_lecture_player
from .storage import (
    list_courses,
    list_lectures,
    load_course,
    load_lecture,
    resolve,
    save_course,
    save_lecture,
    search_courses,
    search_lectures,
)

__all__ = [
    "CourseRecord",
    "LectureRecord",
    "create_course",
    "create_lecture",
    "data_dir",
    "list_courses",
    "list_lectures",
    "load_course",
    "load_lecture",
    "render_course_player",
    "render_lecture_player",
    "resolve",
    "search_courses",
    "search_lectures",
]


def _write_output(payload: dict, output: Optional[Path]) -> None:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_lecture(
    query: str,
    topic: str,
    subject: str,
    duration_minutes: float,
    output: Optional[Path] = None,
) -> LectureRecord:
    subject = normalize_subject(subject)
    ir = build_lecture_ir(topic, subject, duration_minutes, query)
    record = LectureRecord(
        id=new_id(topic),
        query=query,
        topic=topic,
        subject=subject,
        duration_minutes=duration_minutes,
        ir=ir.model_dump(mode="json"),
    )
    save_lecture(record)
    _write_output(record.model_dump(mode="json"), output)
    return record


def create_course(
    query: str,
    topic: str,
    subject: str,
    duration_minutes: float,
    total_episodes: int,
    output: Optional[Path] = None,
) -> CourseRecord:
    subject = normalize_subject(subject)
    course_id = new_id(topic)
    per_episode_minutes = duration_minutes / max(total_episodes, 1)

    episode_ids: list[str] = []
    episodes: list[LectureRecord] = []
    for i in range(total_episodes):
        ep_topic = f"{topic} (episode {i + 1})"
        ir = build_lecture_ir(ep_topic, subject, per_episode_minutes, query)
        ep_record = LectureRecord(
            id=new_id(ep_topic),
            query=query,
            topic=ep_topic,
            subject=subject,
            duration_minutes=per_episode_minutes,
            course_id=course_id,
            episode_index=i,
            ir=ir.model_dump(mode="json"),
        )
        save_lecture(ep_record)
        episode_ids.append(ep_record.id)
        episodes.append(ep_record)

    record = CourseRecord(
        id=course_id,
        query=query,
        topic=topic,
        subject=subject,
        duration_minutes=duration_minutes,
        total_episodes=total_episodes,
        episode_ids=episode_ids,
    )
    save_course(record)
    render_course_player(record, episodes)
    _write_output(
        {
            **record.model_dump(mode="json"),
            "episodes": [ep.model_dump(mode="json") for ep in episodes],
        },
        output,
    )
    return record
