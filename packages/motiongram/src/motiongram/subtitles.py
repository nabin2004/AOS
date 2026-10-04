"""Declarative Typst subtitles (composed in screen space after the camera pass)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    """One subtitle line with Typst body and optional plain text for WebVTT.

    ``voice`` and ``settings`` apply only to :func:`write_webvtt` (not burned-in Typst).
    """

    start: float
    end: float
    typst: str
    plain: str | None = None
    voice: str | None = None
    settings: str | None = None


@dataclass(frozen=True, slots=True)
class SubtitleStyle:
    font_size: float = 22.0
    color: str = "#FFFFFF"
    bottom_margin: float = 48.0
    max_width_ratio: float = 0.92
    line_gap: float = 8.0


@dataclass(frozen=True, slots=True)
class SubtitleTrack:
    cues: tuple[SubtitleCue, ...]
    style: SubtitleStyle = field(default_factory=SubtitleStyle)


def subtitle_typst_layout(*, scene_width_px: float, style: SubtitleStyle) -> tuple[float, float]:
    """Typst page width and text size in pt (96 DPI convention vs Skia pixels)."""
    ratio = 72.0 / 96.0
    page_width_pt = max(float(scene_width_px) * style.max_width_ratio * ratio, 32.0)
    font_size_pt = max(style.font_size * ratio, 6.0)
    return page_width_pt, font_size_pt


def _cue_sort_key(c: SubtitleCue) -> tuple:
    return (c.start, c.end, c.typst, c.plain or "", c.voice or "", c.settings or "")


def sort_cues(cues: Sequence[SubtitleCue]) -> tuple[SubtitleCue, ...]:
    return tuple(sorted(cues, key=_cue_sort_key))


def active_subtitles(track: SubtitleTrack, t: float) -> list[SubtitleCue]:
    out = [c for c in track.cues if c.start <= t < c.end]
    out.sort(key=_cue_sort_key)
    return out


def validate_subtitle_track(track: SubtitleTrack, *, duration: float | None = None) -> list[str]:
    """Return human-readable issues (empty if none). Does not raise."""
    warnings: list[str] = []
    for i, c in enumerate(track.cues):
        pre = f"cue[{i}]"
        if c.start < 0:
            warnings.append(f"{pre}: start {c.start} is negative")
        if c.end <= c.start:
            warnings.append(
                f"{pre}: need end > start [start, end); got start={c.start} end={c.end}"
            )
        if duration is not None:
            if c.start > duration + 1e-6:
                warnings.append(f"{pre}: start {c.start} is after scene duration {duration}")
            if c.end > duration + 1e-6:
                warnings.append(f"{pre}: end {c.end} is past scene duration {duration}")
    return warnings


def _sanitize_webvtt_voice(name: str) -> str:
    """Strip characters that would break WebVTT cue markup."""
    s = name.strip()
    s = s.replace("\n", " ").replace("\r", " ")
    for ch in "<>&":
        s = s.replace(ch, "")
    return " ".join(s.split())


def _format_webvtt_ts(seconds: float) -> str:
    """WebVTT timestamp: period before ms; ``MM:SS.mmm`` when hours is zero."""
    s = max(0.0, float(seconds))
    h = int(s // 3600)
    rem = s - 3600 * h
    m = int(rem // 60)
    sec = rem - 60 * m
    whole = int(sec)
    ms = int(round((sec - whole) * 1000))
    if ms >= 1000:
        whole += 1
        ms = 0
    if whole >= 60:
        m += whole // 60
        whole = whole % 60
    if m >= 60:
        h += m // 60
        m = m % 60

    if h > 0:
        return f"{h:02d}:{m:02d}:{whole:02d}.{ms:03d}"
    return f"{m:02d}:{whole:02d}.{ms:03d}"


def write_webvtt(
    track: SubtitleTrack,
    path: Path | str,
    *,
    scene_duration: float | None = None,
) -> Path:
    """Write a WebVTT sidecar including only cues with non-empty ``plain``.

    ``scene_duration`` is reserved for future note blocks; times are taken from cues.
    """
    _ = scene_duration
    path = Path(path)
    lines: list[str] = ["WEBVTT", ""]
    for c in sort_cues(track.cues):
        if c.plain is None or not str(c.plain).strip():
            continue
        if c.end <= c.start:
            continue
        t0 = _format_webvtt_ts(c.start)
        t1 = _format_webvtt_ts(c.end)
        timing = f"{t0} --> {t1}"
        if c.settings and str(c.settings).strip():
            timing = f"{timing} {str(c.settings).strip()}"
        lines.append(timing)
        payload = str(c.plain).strip()
        if c.voice and str(c.voice).strip():
            sv = _sanitize_webvtt_voice(str(c.voice))
            if sv:
                payload = f"<v {sv}>{payload}"
        lines.append(payload)
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _parse_webvtt_ts(raw: str) -> float:
    """Parse WebVTT timestamp to seconds."""
    s = raw.strip()
    if "." in s:
        head, ms_part = s.rsplit(".", 1)
        ms = int(ms_part.ljust(3, "0")[:3])
    else:
        head = s
        ms = 0
    parts = head.split(":")
    if len(parts) == 3:
        h, m, sec = int(parts[0]), int(parts[1]), int(parts[2])
    elif len(parts) == 2:
        h, m, sec = 0, int(parts[0]), int(parts[1])
    else:
        raise ValueError(f"invalid WebVTT timestamp: {raw!r}")
    return h * 3600 + m * 60 + sec + ms / 1000.0


def read_webvtt(path: Path | str) -> SubtitleTrack:
    """Read a WebVTT file into a :class:`SubtitleTrack`.

    Cue text is stored in both ``typst`` and ``plain`` fields.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or not lines[0].strip().startswith("WEBVTT"):
        raise ValueError(f"not a WebVTT file: {path}")

    cues: list[SubtitleCue] = []
    i = 1
    n = len(lines)

    def skip_blank() -> None:
        nonlocal i
        while i < n and not lines[i].strip():
            i += 1

    skip_blank()
    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if "-->" not in line:
            i += 1
            continue
        timing_parts = line.split("-->")
        if len(timing_parts) != 2:
            i += 1
            continue
        start_raw = timing_parts[0].strip()
        end_and_settings = timing_parts[1].strip()
        end_tokens = end_and_settings.split()
        if not end_tokens:
            i += 1
            continue
        end_raw = end_tokens[0]
        settings = " ".join(end_tokens[1:]) if len(end_tokens) > 1 else None
        i += 1
        text_lines: list[str] = []
        while i < n and lines[i].strip():
            text_lines.append(lines[i].rstrip())
            i += 1
        payload = "\n".join(text_lines).strip()
        if not payload:
            continue
        voice: str | None = None
        if payload.startswith("<v ") and ">" in payload:
            close = payload.index(">")
            voice = payload[3:close].strip()
            payload = payload[close + 1 :].strip()
        cues.append(
            SubtitleCue(
                start=_parse_webvtt_ts(start_raw),
                end=_parse_webvtt_ts(end_raw),
                typst=payload,
                plain=payload,
                voice=voice,
                settings=settings,
            )
        )
        skip_blank()

    return SubtitleTrack(cues=tuple(sort_cues(cues)))
