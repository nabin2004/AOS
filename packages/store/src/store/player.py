"""Dummy HTML "player": a placeholder video box + a transcript derived from the
lecture's narration beats. Good enough to click play on until a real renderer exists.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from .models import CourseRecord, LectureRecord
from .paths import players_dir

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{
    margin: 0; padding: 2rem; background: #0e0e10; color: #f2f2f2;
    font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    display: flex; flex-direction: column; align-items: center;
  }}
  .wrap {{ max-width: 860px; width: 100%; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.25rem; }}
  .meta {{ color: #9a9aa2; font-size: 0.9rem; margin-bottom: 1.25rem; }}
  .player {{
    width: 100%; aspect-ratio: 16 / 9; border-radius: 12px;
    background: linear-gradient(135deg, #3B82F6, #10B981);
    display: flex; align-items: center; justify-content: center;
    position: relative; margin-bottom: 1.5rem;
  }}
  .play-icon {{
    width: 0; height: 0;
    border-top: 28px solid transparent; border-bottom: 28px solid transparent;
    border-left: 46px solid rgba(255,255,255,0.9); margin-left: 8px;
    filter: drop-shadow(0 2px 6px rgba(0,0,0,0.4));
  }}
  .duration {{
    position: absolute; bottom: 10px; right: 14px;
    background: rgba(0,0,0,0.55); padding: 2px 8px; border-radius: 6px;
    font-size: 0.8rem;
  }}
  .transcript {{ border-top: 1px solid #2a2a2e; padding-top: 1rem; }}
  .line {{ display: flex; gap: 1rem; padding: 0.5rem 0; }}
  .ts {{ color: #6a6a72; font-variant-numeric: tabular-nums; min-width: 3.5rem; }}
  .txt {{ flex: 1; line-height: 1.5; }}
  a.episode {{
    display: block; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    background: #1a1a1e; border-radius: 8px; color: #f2f2f2; text-decoration: none;
  }}
  a.episode:hover {{ background: #26262b; }}
  .badge {{ color: #6a6a72; font-size: 0.85rem; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title}</h1>
  <div class="meta">{meta}</div>
  <div class="player">
    <div class="play-icon"></div>
    <div class="duration">{duration}</div>
  </div>
  {body}
</div>
</body>
</html>
"""


def _fmt_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _transcript_html(ir: dict) -> str:
    lines: list[str] = []
    t = 0.0
    for scene in ir.get("scenes", []):
        for beat in scene.get("beats", []):
            narration = beat.get("narration")
            anim_time = sum(op.get("run_time", 0.0) for op in beat.get("animation_segment", []))
            hold = beat.get("hold_seconds", 0.0)
            if narration and narration.get("text"):
                lines.append(
                    f'<div class="line"><div class="ts">{_fmt_ts(t)}</div>'
                    f'<div class="txt">{escape(narration["text"])}</div></div>'
                )
            t += anim_time + hold
    if not lines:
        return '<div class="transcript"><em>No transcript available.</em></div>'
    return '<div class="transcript">' + "".join(lines) + "</div>"


def render_lecture_player(record: LectureRecord) -> Path:
    duration = record.ir.get("duration_target_seconds") or record.duration_minutes * 60
    html = _PAGE.format(
        title=escape(record.topic),
        meta=escape(f"{record.subject} · {record.duration_minutes:.0f} min · id: {record.id}"),
        duration=_fmt_ts(duration),
        body=_transcript_html(record.ir),
    )
    path = players_dir() / f"{record.id}.html"
    path.write_text(html, encoding="utf-8")
    return path


def render_course_player(record: CourseRecord, episodes: list[LectureRecord]) -> Path:
    for ep in episodes:
        render_lecture_player(ep)

    items = "".join(
        f'<a class="episode" href="{ep.id}.html">'
        f"Episode {i + 1}: {escape(ep.topic)} "
        f'<span class="badge">({ep.duration_minutes:.0f} min)</span></a>'
        for i, ep in enumerate(episodes)
    )
    body = f'<div class="transcript"><h3>Episodes</h3>{items}</div>'
    html = _PAGE.format(
        title=escape(record.topic),
        meta=escape(
            f"{record.subject} · course · {record.total_episodes} episodes · id: {record.id}"
        ),
        duration=_fmt_ts(record.duration_minutes * 60),
        body=body,
    )
    path = players_dir() / f"{record.id}.html"
    path.write_text(html, encoding="utf-8")
    return path
